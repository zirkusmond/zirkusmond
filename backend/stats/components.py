import json

from django.db import models
from unfold.components import BaseComponent, register_component

from reservations.payments.models import Payment

from .models import PageView
from .ranges import range_bucket_labels, range_since, resolve_range


@register_component
class VisitorsLineChart(BaseComponent):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        range_spec = resolve_range(self.request)
        since = range_since(range_spec)
        buckets = range_bucket_labels(range_spec, since)
        counts_by_bucket = PageView.objects.visits_per_bucket(range_spec.trunc, since=since)

        # Query completed payments per bucket
        payments_qs = Payment.objects.filter(status=Payment.Status.COMPLETED)
        if since:
            payments_qs = payments_qs.filter(created_at__gte=since)

        payments_by_bucket = dict(
            payments_qs.annotate(bucket=range_spec.trunc("created_at"))
            .values("bucket")
            .annotate(count=models.Count("id"))
            .values_list("bucket", "count")
        )

        context.update(
            {
                "height": 300,
                "data": json.dumps(
                    {
                        "labels": [bucket.strftime(range_spec.bucket_format) for bucket in buckets],
                        "datasets": [
                            {
                                "label": "Visits",
                                "data": [counts_by_bucket.get(bucket, 0) for bucket in buckets],
                                "borderColor": "var(--color-primary-600)",
                                "backgroundColor": "var(--color-primary-200)",
                                "displayYAxis": True,
                            },
                            {
                                "label": "Payments",
                                "data": [payments_by_bucket.get(bucket, 0) for bucket in buckets],
                                "borderColor": "var(--color-green-600)",
                                "backgroundColor": "var(--color-green-200)",
                                "displayYAxis": True,
                            },
                        ],
                    }
                ),
            }
        )
        return context


@register_component
class DeviceBreakdownBarChart(BaseComponent):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        range_spec = resolve_range(self.request)
        since = range_since(range_spec)
        breakdown = PageView.objects.device_breakdown(since=since)

        device_choices = list(PageView.DeviceChoices)

        context.update(
            {
                "height": 300,
                "data": json.dumps(
                    {
                        "labels": [choice.label for choice in device_choices],
                        "datasets": [
                            {
                                "label": "Sessions by device",
                                "data": [
                                    breakdown.get(choice.value, 0) for choice in device_choices
                                ],
                                "backgroundColor": "var(--color-primary-600)",
                                "displayYAxis": True,
                            }
                        ],
                    }
                ),
            }
        )
        return context
