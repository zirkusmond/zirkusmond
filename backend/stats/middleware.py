from django.utils import timezone

from .models import PageView

# Server-to-server callers that never represent a visitor looking at a page.
_NON_PAGE_VIEW_PATHS = ("/payments/webhook/stripe",)


class PageViewMiddleware:
    # run once at server startup
    # stores get_response, which returns either another middleware or the actual view
    def __init__(self, get_response):
        self.get_response = get_response

    # this method will run on every single request
    def __call__(self, request):
        response = self.get_response(request)

        if request.path.startswith(("/mondmin", "/static", "/media", "/api")):
            return response

        if request.path in _NON_PAGE_VIEW_PATHS:
            return response

        # TanStack Router's hover/touch "intent" preloading fires a real loader
        # request ahead of navigation; the frontend marks these so they don't get
        # counted as a page the visitor actually looked at.
        if request.META.get("HTTP_X_PRELOAD") == "1":
            return response

        # Skip SSR internal requests: the frontend's Node.js server fetches from
        # Django at 127.0.0.1 to render pages server-side. These aren't visitors.
        user_agent = request.META.get("HTTP_USER_AGENT", "").lower()
        if request.META.get("REMOTE_ADDR") == "127.0.0.1" and user_agent == "node":
            return response
        if PageView.detect_device(user_agent) == PageView.DeviceChoices.BOT:
            return response

        if not request.session.session_key:
            request.session.save()  # force a session_key to exist

        session_key = request.session.session_key

        # close out the previous pageview in this session -> gives us "time on page"
        last = (
            PageView.objects.filter(session_key=session_key, left_at__isnull=True)
            .order_by("-entered_at")
            .first()
        )

        if last:
            last.left_at = timezone.now()
            last.save(update_fields=["left_at"])

        # create new pageView. left_at is now null on this pv
        PageView.objects.create(
            session_key=session_key,
            path=request.path,
            referer=request.META.get("HTTP_REFERER", ""),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
            ip_address=request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip() or None,
            device_type=PageView.detect_device(user_agent),
        )

        return response
