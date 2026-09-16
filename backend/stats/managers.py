from django.db import models


class PageViewManager(models.Manager):
    def bounce_rate(self, since=None):
        qs = self.get_queryset()
        if since:
            qs = qs.filter(entered_at__gte=since)

        sessions = qs.values("session_key").annotate(views=models.Count("id"))

        total = sessions.count()

        if not total:
            return 0.0

        bounced = sessions.filter(views=1).count()
        return round(bounced / total * 100, 2)

    def avg_time_on_site(self, since=None):
        from datetime import timedelta

        qs = self.get_queryset().filter(left_at__isnull=False)

        if since:
            qs = qs.filter(entered_at__gte=since)

        # Exclude abandoned tabs left open overnight (durations > 30 minutes).
        max_duration = timedelta(minutes=30)
        result = (
            qs.annotate(duration=models.F("left_at") - models.F("entered_at"))
            .filter(duration__lte=max_duration)
            .aggregate(avg=models.Avg("duration"))
        )

        return result["avg"]

    def device_breakdown(self, since=None) -> dict:
        qs = self.get_queryset()

        if since:
            qs = qs.filter(entered_at__gte=since)

        return dict(
            qs.values("device_type")
            .annotate(count=models.Count("id"))
            .values_list("device_type", "count")
        )

    def visits_per_bucket(self, trunc_cls, since=None) -> dict:
        """Unique-visit (distinct session) counts per Trunc* time bucket, excluding bots --
        same bucket-key alignment as views_per_bucket(), see stats/ranges.py.
        """
        qs = self.get_queryset().exclude(device_type=self.model.DeviceChoices.BOT)

        if since:
            qs = qs.filter(entered_at__gte=since)

        return dict(
            qs.annotate(bucket=trunc_cls("entered_at"))
            .values("bucket")
            .annotate(count=models.Count("session_key", distinct=True))
            .values_list("bucket", "count")
        )
