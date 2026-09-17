from django.db import models

from .managers import PageViewManager


class PageView(models.Model):
    class DeviceChoices(models.TextChoices):
        MOBILE = "mobile"
        TABLET = "tablet"
        DESKTOP = "desktop"
        BOT = "bot"

    session_key = models.CharField(max_length=40, db_index=True)
    path = models.CharField(max_length=255)
    referer = models.CharField(max_length=255, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    device_type = models.CharField(max_length=10, choices=DeviceChoices)

    entered_at = models.DateTimeField(auto_now_add=True)
    left_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["session_key", "entered_at"])]

    objects = PageViewManager()

    BOT_KEYWORDS = (
        "bot",
        "spider",
        "crawl",
        "slurp",
        "facebookexternalhit",
        "whatsapp",
        "telegram",
        "headlesschrome",
        "phantomjs",
        "python-requests",
        "python-httpx",
        "curl/",
        "wget/",
        "okhttp",
        "go-http-client",
        "postmanruntime",
        "node-fetch",
        "axios/",
        "scrapy",
        # AI crawlers
        "anthropic-ai",
        "claude-web",
        "cohere-ai",
        "gptbot",
        "chatgpt",
        "bingpreview",
        "perplexitybot",
        "youbot",
        "mistralai",
        "hunyuan",
        # Meta link-preview crawlers
        "externalagent",
        "externalads",
        "webindexer",
        # Others not covered by generic "bot"/"spider"
        "applebot",
        "claude-user",
    )

    @classmethod
    def detect_device(cls, user_agent: str) -> str:
        ua = user_agent.lower()
        if any(kw in ua for kw in cls.BOT_KEYWORDS):
            return cls.DeviceChoices.BOT
        if any(kw in ua for kw in ("ipad", "tablet")):
            return cls.DeviceChoices.TABLET
        if any(kw in ua for kw in ("mobi", "android", "iphone")):
            return cls.DeviceChoices.MOBILE

        return cls.DeviceChoices.DESKTOP
