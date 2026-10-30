from datetime import date, datetime, timedelta
from datetime import time as dtime
from typing import Any

from django import forms
from django.conf import settings
from django.contrib import admin, messages
from django.core import signing
from django.core.mail import send_mail
from django.db.models import (
    Count,
    F,
    IntegerField,
    Min,
    OuterRef,
    Prefetch,
    QuerySet,
    Subquery,
    Sum,
    Value,
)
from django.db.models.functions import Coalesce
from django.http import HttpRequest
from django.utils import timezone
from tinymce.widgets import TinyMCE
from unfold.admin import ModelAdmin
from unfold.widgets import UnfoldAdminEmailInputWidget

from events.models import Event
from events.stats import STATS_TOKEN_SALT
from reservations.models import Guest, Payment

from .models import PastShow, Show, UnscheduledShow, UpcomingShow


class EventInlineForm(forms.ModelForm):
    event_date = forms.DateField(
        label="Event date",
        widget=forms.DateInput(
            attrs={"type": "text", "class": "event-date-input", "placeholder": "dd/mm/yy"},
            format="%d/%m/%y",
        ),
        input_formats=["%d/%m/%y"],
        required=True,
    )
    show_time = forms.TimeField(
        label="Show time",
        widget=forms.TimeInput(
            attrs={"type": "time", "class": "event-time-input"},
            format="%H:%M",
        ),
        input_formats=["%H:%M"],
        required=True,
    )
    admission_time = forms.TimeField(
        label="Admission time",
        widget=forms.TimeInput(
            attrs={"type": "time", "class": "admission-time-input"},
            format="%H:%M",
        ),
        input_formats=["%H:%M"],
        required=False,
        help_text="Defaults to one hour before the show.",
    )

    class Meta:
        model = Event
        fields = (
            "event_date",
            "show_time",
            "admission_time",
            "reservation_capacity",
            "open_for_reservation",
        )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        if self.instance.pk and self.instance.begin:
            local_begin = timezone.localtime(self.instance.begin)
            self.fields["event_date"].initial = local_begin.date()
            self.fields["show_time"].initial = local_begin.time().replace(second=0, microsecond=0)
            if self.instance.admission:
                local_admission = timezone.localtime(self.instance.admission)
                self.fields["admission_time"].initial = local_admission.time().replace(
                    second=0, microsecond=0
                )
        else:
            today = timezone.localdate()
            default_time = self._default_show_time_for_date(today)
            self.fields["event_date"].initial = today
            self.fields["show_time"].initial = default_time
            self.fields["admission_time"].initial = (
                datetime.combine(today, default_time) - timedelta(hours=1)
            ).time()

    def _default_show_time_for_date(self, date_value: date) -> dtime:
        return dtime(hour=20, minute=0)

    def clean(self) -> dict[str, Any]:
        cleaned_data = super().clean() or {}
        event_date = cleaned_data.get("event_date")
        show_time = cleaned_data.get("show_time")
        if not event_date:
            raise forms.ValidationError("Please provide a date for the event.")
        if not show_time:
            show_time = self._default_show_time_for_date(event_date)

        combined = datetime.combine(event_date, show_time)
        begin_dt = timezone.make_aware(combined, timezone.get_current_timezone())
        cleaned_data["begin"] = begin_dt

        admission = cleaned_data.get("admission")
        admission_time = cleaned_data.get("admission_time")
        if admission_time:
            admission = timezone.make_aware(
                datetime.combine(event_date, admission_time), timezone.get_current_timezone()
            )
        elif admission is None:
            admission = begin_dt - timedelta(hours=1)

        cleaned_data["admission"] = admission
        cleaned_data["computed_begin"] = begin_dt
        cleaned_data["computed_admission"] = admission
        return cleaned_data

    def _post_clean(self) -> None:
        begin = (self.cleaned_data or {}).get("computed_begin")
        admission = (self.cleaned_data or {}).get("computed_admission")
        if begin:
            self.instance.begin = begin
        if admission:
            self.instance.admission = admission
        super()._post_clean()  # type: ignore[misc]  # Django-internal, not in django-stubs

    def has_changed(self) -> bool:
        if not self.instance.pk and self.data:
            prefix = self.prefix
            event_date_key = f"{prefix}-event_date" if prefix else "event_date"
            if self.data.get(event_date_key):
                return True
        return super().has_changed()

    def save(self, commit: bool = True) -> Event:
        instance = super().save(commit=False)
        begin_dt = self.cleaned_data.get("computed_begin") or self.cleaned_data.get("begin")
        admission_dt = self.cleaned_data.get("computed_admission") or self.cleaned_data.get(
            "admission"
        )

        if begin_dt:
            instance.begin = begin_dt
        if admission_dt:
            instance.admission = admission_dt

        if commit:
            instance.save()
            self.save_m2m()
        return instance


class ShowForm(forms.ModelForm):
    description = forms.CharField(widget=TinyMCE(), required=False)
    cast = forms.CharField(widget=TinyMCE(), required=False)

    class Meta:
        model = Show
        fields = "__all__"


class EventInline(admin.TabularInline):
    model = Event
    form = EventInlineForm
    fields = (
        "event_date",
        "show_time",
        "admission_time",
        "reservation_capacity",
        "open_for_reservation",
    )
    extra = 0
    show_change_link = True

    class Media:
        js = ("events/js/event_inline.js",)


class ShowAdmin(ModelAdmin):
    form = ShowForm
    list_display = ["title", "next_event_date", "dates_text", "reservation_open", "show_in_preview"]
    list_filter = ["private", "last_modified"]
    search_fields = ["title", "description", "cast"]
    ordering: list[str] = []
    default_ordering = [F("next_event_begin").desc(nulls_last=True), "-title"]
    inlines = [EventInline]

    def get_queryset(self, request: HttpRequest) -> QuerySet[Show]:
        queryset = super().get_queryset(request)
        events_for_show = Event.objects.filter(show=OuterRef("pk"))
        capacity_subquery = events_for_show.annotate(
            total_capacity=Sum("reservation_capacity")
        ).values("total_capacity")[:1]

        confirmed_reservations_subquery = (
            Payment.objects.filter(
                reservation__event__show=OuterRef("pk"),
                status=Payment.Status.COMPLETED,
            )
            .values("reservation__event__show")
            .annotate(total_reservations=Count("reservation", distinct=True))
            .values("total_reservations")[:1]
        )

        confirmed_guests_subquery = (
            Guest.objects.filter(
                reservation__event__show=OuterRef("pk"),
                reservation__payment__status=Payment.Status.COMPLETED,
            )
            .values("reservation__event__show")
            .annotate(total_guests=Count("pk", distinct=True))
            .values("total_guests")[:1]
        )

        event_reservations = (
            Payment.objects.filter(
                reservation__event=OuterRef("pk"),
                status=Payment.Status.COMPLETED,
            )
            .values("reservation__event")
            .annotate(count=Count("reservation", distinct=True))
            .values("count")
        )

        event_guests = (
            Guest.objects.filter(
                reservation__event=OuterRef("pk"),
                reservation__payment__status=Payment.Status.COMPLETED,
            )
            .values("reservation__event")
            .annotate(count=Count("pk", distinct=True))
            .values("count")
        )

        events_queryset = Event.objects.order_by("admission").annotate(
            annotated_reservation_count=Coalesce(
                Subquery(event_reservations, output_field=IntegerField()),
                Value(0),
                output_field=IntegerField(),
            )
            + Coalesce(
                Subquery(event_guests, output_field=IntegerField()),
                Value(0),
                output_field=IntegerField(),
            )
        )

        queryset = queryset.prefetch_related(Prefetch("events", queryset=events_queryset)).annotate(
            next_event_begin=Min("events__begin"),
            annotated_total_capacity=Coalesce(
                Subquery(capacity_subquery, output_field=IntegerField()),
                Value(0),
                output_field=IntegerField(),
            ),
            annotated_confirmed_reservations=Coalesce(
                Subquery(confirmed_reservations_subquery, output_field=IntegerField()),
                Value(0),
                output_field=IntegerField(),
            ),
            annotated_confirmed_guests=Coalesce(
                Subquery(confirmed_guests_subquery, output_field=IntegerField()),
                Value(0),
                output_field=IntegerField(),
            ),
        )
        if "o" not in request.GET and getattr(self, "default_ordering", None):
            queryset = queryset.order_by(*self.default_ordering)
        return queryset

    @admin.display(ordering="next_event_begin", description="Next event")
    def next_event_date(self, obj: Show) -> str:
        next_begin = getattr(obj, "next_event_begin", None)
        if not next_begin:
            return "-"
        return timezone.localtime(next_begin).strftime("%d.%m.%y %H:%M")


class UpcomingShowAdminForm(ShowForm):
    organiser_email = forms.EmailField(
        required=False,
        help_text="Enter an email to send a secret access link for this show",
        label="Organiser email",
        widget=UnfoldAdminEmailInputWidget(),
    )


class UpcomingShowAdmin(ShowAdmin):
    form = UpcomingShowAdminForm

    def save_model(self, request: HttpRequest, obj: UpcomingShow, form: Any, change: bool) -> None:
        super().save_model(request, obj, form, change)
        email = (form.cleaned_data.get("organiser_email") or "").lower().strip()
        if email:
            self._send_organiser_link(obj, email)
            messages.success(request, f"Access link sent to {email} for “{obj}”.")

    def _send_organiser_link(self, obj: UpcomingShow, email: str) -> None:
        token = signing.dumps({"show_id": obj.pk}, salt=STATS_TOKEN_SALT)

        sales_url = f"{settings.FRONTEND_URL}/shows/{obj.pk}/stats?token={token}"

        send_mail(
            "Your show ticket sales link",
            f"Hello, \nwith this link you can directly view your current ticket sales for all events of your show {obj}: {sales_url}.",
            settings.DEFAULT_FROM_EMAIL,
            [email],
        )


admin.site.register(UpcomingShow, UpcomingShowAdmin)
admin.site.register(UnscheduledShow, ShowAdmin)
admin.site.register(PastShow, ShowAdmin)
admin.site.register(Show, ShowAdmin)
