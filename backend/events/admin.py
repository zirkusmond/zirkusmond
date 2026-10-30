from io import BytesIO

import xlsxwriter
from django import forms
from django.contrib import admin, messages
from django.db.models import QuerySet
from django.db.models.functions import Lower
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from unfold.admin import ModelAdmin
from unfold.decorators import action
from unfold.forms import BaseDialogForm
from xlsxwriter.worksheet import Worksheet

from events.models import Event, PastEvent, UpcomingEvent
from events.stats import with_event_stats
from reservations.models import Guest, Payment, Reservation
from reservations.payments.admin import reservation_to_dict, send_email_to_reservants
from reservations.tasks import refund_payment


class CancelEventForm(BaseDialogForm):
    confirm = forms.CharField(label="Type REFUND to confirm")

    def clean_confirm(self):
        value = self.cleaned_data["confirm"]
        if value != "REFUND":
            raise forms.ValidationError("Type REFUND exactly.")
        return value


class BaseEventAdmin(ModelAdmin):
    list_display = [
        "show",
        "begin",
        "time_and_date",
        "reservation_open",
        "reserved_tickets",
        "revenue",
    ]
    search_fields = ["show__title"]
    actions = ["print_reservations", "send_to_reservants"]
    actions_detail = ["send_mail_to_reservants_detail", "cancel_event"]
    ordering = ["-begin"]
    date_hierarchy = "begin"

    class Media:
        css = {
            "all": ("admin/css/mobile-responsive-admin.css",),
        }

    def get_queryset(self, request: HttpRequest) -> QuerySet[Event]:
        queryset = super().get_queryset(request)
        queryset = queryset.select_related("show")
        return with_event_stats(queryset)

    @admin.display(description="Revenue", ordering="total_revenue")
    def revenue(self, obj: Event) -> str:
        total_revenue = getattr(obj, "total_revenue", None)
        if total_revenue is None:
            return "—"
        return f"€ {total_revenue:.2f}"

    @admin.action(description="Print Reservation List")
    def print_reservations(
        self, request: HttpRequest, queryset: QuerySet[Event]
    ) -> HttpResponse | None:
        for event in queryset:
            payments = Payment.objects.filter(
                reservation__event=event, status=Payment.Status.COMPLETED
            ).order_by(Lower("reservation__last_name"))
            reservations = [payment.reservation for payment in payments if payment.reservation]

            output = BytesIO()
            workbook = xlsxwriter.Workbook(output)
            worksheet = workbook.add_worksheet()
            worksheet.set_landscape()
            worksheet.set_paper(9)  # A4
            worksheet.set_column(0, 3, 15)

            bold = workbook.add_format({"bold": True, "border": 1})
            border = workbook.add_format({"border": 1})

            columns = ["first_name", "last_name", "email", f"{event.date_str()}"]

            def add_row(
                worksheet: Worksheet, row: int, person: Reservation | Guest, count: int
            ) -> None:
                worksheet.write_row(
                    row,
                    0,
                    [
                        person.first_name,
                        person.last_name,
                        getattr(person, "email", ""),
                        count,
                    ],
                    border,
                )

            worksheet.write_row(0, 0, columns, bold)
            worksheet.repeat_rows(0)
            row = 1
            for reservation in reservations:
                add_row(worksheet, row, reservation, row)
                worksheet.write(row, 0, reservation.first_name, bold)
                row += 1

                for guest in Guest.objects.filter(reservation=reservation):
                    add_row(worksheet, row, guest, row)
                    row += 1

            workbook.close()
            xlsx_data = output.getvalue()

            filename = event.admission.astimezone().strftime("reservation_list_%Y-%m-%d.xlsx")
            response = HttpResponse(
                headers={"Content-Disposition": f'inline; filename="{filename}"'},
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            response.write(xlsx_data)
            return response
        return None

    @admin.action(description="Send mail to Reservants")
    def send_to_reservants(self, request: HttpRequest, queryset: QuerySet[Event]) -> HttpResponse:
        all_payments: list[Payment] = []
        for event in queryset:
            all_payments += list(
                Payment.objects.filter(status=Payment.Status.COMPLETED, reservation__event=event)
            )
        dicts = [
            reservation_to_dict(payment.reservation)
            for payment in all_payments
            if payment.reservation
        ]
        return send_email_to_reservants(request, dicts, self)

    @action(description="Send mail to Reservants", url_path="send-mail", icon="mail")
    def send_mail_to_reservants_detail(self, request: HttpRequest, object_id: str) -> HttpResponse:
        payments = Payment.objects.filter(
            status=Payment.Status.COMPLETED, reservation__event_id=object_id
        )
        dicts = [reservation_to_dict(p.reservation) for p in payments if p.reservation]
        return send_email_to_reservants(request, dicts, self)

    @action(
        description="Cancel Event and refund all Payments",
        dialog={
            "title": "Cancel event?",
            "description": "Every completed payment will be refunded via Stripe. This cannot be undone.",
            "submit_text": "Refund everyone",
            "form_class": CancelEventForm,
        },
        icon="x",
    )
    def cancel_event(self, request: HttpRequest, form: forms.Form, object_id: str):
        event = get_object_or_404(Event, pk=int(object_id))
        event.open_for_reservation = False
        event.save()

        payments_to_refund_ids = Payment.objects.filter(
            status=Payment.Status.COMPLETED, reservation__event_id=object_id
        ).values_list("pk", flat=True)
        for pk in payments_to_refund_ids:
            refund_payment.delay(str(pk))

        messages.success(request, f"Queued {len(payments_to_refund_ids)} refunds.")

        return HttpResponse(
            headers={"HX-Redirect": reverse_lazy("admin:events_upcomingevent_changelist")}
        )


class EventAdmin(BaseEventAdmin):
    list_filter = ["begin"]


class UpcomingEventAdmin(BaseEventAdmin):
    list_filter = ["open_for_reservation"]


class PastEventAdmin(BaseEventAdmin):
    list_filter: list[str] = []


admin.site.register(Event, EventAdmin)
admin.site.register(UpcomingEvent, UpcomingEventAdmin)
admin.site.register(PastEvent, PastEventAdmin)
