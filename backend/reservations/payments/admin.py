from typing import Any

from django.contrib import admin
from django.db.models import Count, Prefetch, QuerySet
from django.http import HttpRequest, HttpResponseRedirect
from django.template import Context, Template
from django.template.response import TemplateResponse
from django.utils import timezone
from payments import PaymentStatus
from unfold.admin import ModelAdmin

from events.forms import EmailTextForm
from reservations import emails, tasks
from reservations.models import Reservation, ReservationPayment
from reservations.payments.models import Payment


def reservation_to_dict(reservation: Reservation) -> dict[str, Any]:
    event = reservation.event
    show = event.show if event else None
    return {
        "show_title": show.title if show else "",
        "event_time": event.time_and_date() if event else "",
        "firstname": reservation.first_name,
        "surname": reservation.last_name,
        "email": reservation.email,
    }


def render_mail(subject: str, body: str, context: dict[str, Any]) -> tuple[str, str]:
    template_context = Context(context)
    rendered_subject = Template(subject).render(template_context)
    rendered_body = Template(body).render(template_context)
    return rendered_subject, rendered_body


def send_email_to_reservants(
    request: HttpRequest, dicts: list[dict[str, Any]], admin_instance: ModelAdmin
) -> HttpResponseRedirect | TemplateResponse:
    if "text_field" in request.POST.keys():
        form = EmailTextForm(request.POST)
    else:
        form = EmailTextForm()
    sample_text, sample_subject = None, ""
    if form.is_valid():
        mail_text = form.data["text_field"]
        mail_subject = form.data["subject"]
        sample_subject, sample_text = render_mail(mail_subject, mail_text, dicts[0])

        if "send" in request.POST.keys():
            for reservation_dict in dicts:
                subject, text = render_mail(mail_subject, mail_text, reservation_dict)
                tasks.send_custom_email.delay(
                    f"{reservation_dict['firstname']} {reservation_dict['surname']}",
                    reservation_dict["email"],
                    subject,
                    text,
                )

            return HttpResponseRedirect(request.get_full_path())

    context = {
        **admin.site.each_context(request),
        "data": dicts,
        "form": form,
        "sample_text": sample_text,
        "sample_subject": sample_subject,
        "action": request.POST.get("action", ""),
        "select_across": request.POST.get("select_across", "0"),
        "index": request.POST.get("index", "0"),
        "selected_action": request.POST.getlist("_selected_action"),
    }
    return TemplateResponse(request, "admin/send_email.html", context)


class ReservationPaymentStatusFilter(admin.SimpleListFilter):
    title = "Status"
    parameter_name = "status"

    def lookups(self, request: HttpRequest, model_admin: admin.ModelAdmin) -> list[tuple[str, str]]:
        return [
            (PaymentStatus.WAITING, "Waiting"),
            (PaymentStatus.CONFIRMED, "Confirmed"),
            (PaymentStatus.REJECTED, "Rejected"),
            (PaymentStatus.REFUNDED, "Refunded"),
            (PaymentStatus.ERROR, "Error"),
        ]

    def queryset(
        self, request: HttpRequest, queryset: QuerySet[ReservationPayment]
    ) -> QuerySet[ReservationPayment]:
        if self.value():
            return queryset.filter(status=self.value())
        return queryset


class ReservationPaymentEventFilter(admin.SimpleListFilter):
    title = "Event"
    parameter_name = "event"

    def lookups(self, request: HttpRequest, model_admin: admin.ModelAdmin) -> list[tuple[str, str]]:
        return [
            ("upcoming", "Upcoming"),
            ("past", "Past"),
        ]

    def queryset(
        self, request: HttpRequest, queryset: QuerySet[ReservationPayment]
    ) -> QuerySet[ReservationPayment]:
        now = timezone.now()
        if self.value() == "upcoming":
            return queryset.filter(reservation__event__begin__gte=now)
        elif self.value() == "past":
            return queryset.filter(reservation__event__begin__lt=now)
        return queryset


class ReservationPaymentAdmin(ModelAdmin):
    list_display = [
        "reservation",
        "status",
        "ticket_count",
        "ticket_price",
        "confirmed_total",
        "variant",
        "event",
        "created",
    ]
    ordering = ["-created"]
    date_hierarchy = "created"
    list_filter = (ReservationPaymentStatusFilter, "variant", ReservationPaymentEventFilter)
    search_fields = [
        "reservation__first_name",
        "reservation__last_name",
        "billing_email",
    ]
    readonly_fields = ["reservation"]
    actions = ["resend_confirmation_mail", "send_to_reservants"]

    def get_queryset(self, request: HttpRequest) -> QuerySet[ReservationPayment]:
        queryset = super().get_queryset(request)
        reservation_queryset = Reservation.objects.select_related("event__show").annotate(
            annotated_guest_count=Count("guests", distinct=True)
        )
        return queryset.prefetch_related(Prefetch("reservation", queryset=reservation_queryset))

    @admin.display(description="Total")
    def confirmed_total(self, obj: ReservationPayment) -> str:
        if obj.status != PaymentStatus.CONFIRMED:
            return "€ 0.00"
        return f"€ {obj.total:.2f}"

    @admin.action(description="Resend confirmation E-Mail")
    def resend_confirmation_mail(
        self, request: HttpRequest, queryset: QuerySet[ReservationPayment]
    ) -> None:
        for payment in queryset:
            if payment.reservation:
                emails.send_confirmation_mail(payment.reservation)

    @admin.action(description="Send mail to Reservants")
    def send_to_reservants(
        self, request: HttpRequest, queryset: QuerySet[ReservationPayment]
    ) -> HttpResponseRedirect | TemplateResponse:
        dicts = [
            reservation_to_dict(payment.reservation) for payment in queryset if payment.reservation
        ]
        return send_email_to_reservants(request, dicts, self)


admin.site.register(ReservationPayment, ReservationPaymentAdmin)


class PaymentStatusFilter(admin.SimpleListFilter):
    title = "Status"
    parameter_name = "status"

    def lookups(self, request: HttpRequest, model_admin: admin.ModelAdmin) -> list[tuple[str, str]]:
        return [
            (Payment.Status.PENDING, "Pending"),
            (Payment.Status.COMPLETED, "Completed"),
            (Payment.Status.FAILED, "Failed"),
            (Payment.Status.REFUNDED, "Refunded"),
            (Payment.Status.ABANDONED, "Abandoned"),
        ]

    def queryset(self, request: HttpRequest, queryset: QuerySet[Payment]) -> QuerySet[Payment]:
        if self.value():
            return queryset.filter(status=self.value())
        return queryset


class PaymentEventFilter(admin.SimpleListFilter):
    title = "Event"
    parameter_name = "event"

    def lookups(self, request: HttpRequest, model_admin: admin.ModelAdmin) -> list[tuple[str, str]]:
        return [
            ("upcoming", "Upcoming"),
            ("past", "Past"),
        ]

    def queryset(self, request: HttpRequest, queryset: QuerySet[Payment]) -> QuerySet[Payment]:
        now = timezone.now()
        if self.value() == "upcoming":
            return queryset.filter(reservation__event__begin__gte=now)
        elif self.value() == "past":
            return queryset.filter(reservation__event__begin__lt=now)
        return queryset


class PaymentAdmin(ModelAdmin):
    list_display = [
        "reservation",
        "status",
        "created_at",
        "event",
        "ticket_count",
        "ticket_price",
        "confirmed_total",
        "payment_method",
    ]
    ordering = ["-created_at"]
    date_hierarchy = "created_at"
    list_filter = (PaymentStatusFilter, "payment_method", PaymentEventFilter)
    search_fields = [
        "reservation__first_name",
        "reservation__last_name",
        "reservation__email",
    ]
    readonly_fields = ["reservation", "stripe_session_id", "stripe_payment_intent_id"]
    actions = ["resend_confirmation_mail", "send_to_reservants"]

    def get_queryset(self, request: HttpRequest) -> QuerySet[Payment]:
        queryset = super().get_queryset(request)
        reservation_queryset = Reservation.objects.select_related("event__show").annotate(
            annotated_guest_count=Count("guests", distinct=True)
        )
        return queryset.prefetch_related(Prefetch("reservation", queryset=reservation_queryset))

    @admin.display(description="Total")
    def confirmed_total(self, obj: Payment) -> str:
        if obj.status != Payment.Status.COMPLETED:
            return "€ 0.00"
        return f"€ {obj.total:.2f}"

    @admin.action(description="Resend confirmation E-Mail")
    def resend_confirmation_mail(self, request: HttpRequest, queryset: QuerySet[Payment]) -> None:
        for payment in queryset:
            if payment.reservation:
                emails.send_confirmation_mail(payment.reservation)

    @admin.action(description="Send mail to Reservants")
    def send_to_reservants(
        self, request: HttpRequest, queryset: QuerySet[Payment]
    ) -> HttpResponseRedirect | TemplateResponse:
        dicts = [
            reservation_to_dict(payment.reservation) for payment in queryset if payment.reservation
        ]
        return send_email_to_reservants(request, dicts, self)


admin.site.register(Payment, PaymentAdmin)
