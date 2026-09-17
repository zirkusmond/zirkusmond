import os

from django.templatetags.static import static

FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")

UNFOLD = {
    "SITE_TITLE": "Zirkusmond admin panel",
    "SITE_HEADER": "Zirkusmond",
    "SITE_SUBHEADER": "Admin Panel",
    "DASHBOARD_CALLBACK": "stats.dashboard.dashboard_callback",
    "SITE_ICON": lambda request: static("images/logo.webp"),
    "SITE_FAVICONS": [
        {
            "rel": "icon",
            "sizes": "32x32",
            "type": "image/png",
            "href": lambda request: static("images/logo.webp"),
        },
    ],
    "STYLES": [
        lambda request: static("css/admin-custom.css"),
    ],
    "SIDEBAR": {
        "show_search": False,
        "show_all_applications": False,
        "navigation": [
            {
                "title": "Tools",
                "separator": True,
                "items": [
                    {
                        "title": "QR Scanner",
                        "icon": "qr_code_scanner",
                        "link": lambda request: f"{FRONTEND_URL}/qr-scanner",
                    },
                ],
            },
            {
                "title": "Events",
                "separator": True,
                "items": [
                    {
                        "title": "Upcoming events",
                        "icon": "event",
                        "link": "/mondmin/events/upcomingevent/",
                    },
                    {
                        "title": "Past events",
                        "icon": "history",
                        "link": "/mondmin/events/pastevent/",
                    },
                    {
                        "title": "All events",
                        "icon": "calendar_month",
                        "link": "/mondmin/events/event/",
                    },
                ],
            },
            {
                "title": "Shows",
                "separator": True,
                "items": [
                    {
                        "title": "Upcoming shows",
                        "icon": "theater_comedy",
                        "link": "/mondmin/shows/upcomingshow/",
                    },
                    {
                        "title": "Unscheduled shows",
                        "icon": "event_busy",
                        "link": "/mondmin/shows/unscheduledshow/",
                    },
                    {
                        "title": "Past shows",
                        "icon": "history",
                        "link": "/mondmin/shows/pastshow/",
                    },
                    {
                        "title": "All shows",
                        "icon": "theaters",
                        "link": "/mondmin/shows/show/",
                    },
                ],
            },
            {
                "title": "Reservations",
                "separator": True,
                "items": [
                    {
                        "title": "Reservations",
                        "icon": "confirmation_number",
                        "link": "/mondmin/reservations/reservation/",
                    },
                    {
                        "title": "Guests",
                        "icon": "person",
                        "link": "/mondmin/reservations/guest/",
                    },
                    {
                        "title": "Payments (Old)",
                        "icon": "payment",
                        "link": "/mondmin/reservations/reservationpayment/",
                    },
                    {
                        "title": "Payments (New)",
                        "icon": "credit_card",
                        "link": "/mondmin/reservations/payment/",
                    },
                ],
            },
            {
                "title": "Content",
                "separator": True,
                "items": [
                    {
                        "title": "Newsletter",
                        "icon": "mail",
                        "link": "/mondmin/newsletter/newsletterregistration/",
                    },
                    {
                        "title": "Homepage elements",
                        "icon": "code",
                        "link": "/mondmin/homepage_elements/",
                    },
                    {
                        "title": "Rentals",
                        "icon": "storefront",
                        "link": "/mondmin/rentals/rental/",
                    },
                ],
            },
            {
                "title": "Statistics",
                "separator": True,
                "items": [
                    {
                        "title": "Stats",
                        "icon": "analytics",
                        "link": "/mondmin/stats/",
                    },
                ],
            },
            {
                "title": "Users & Auth",
                "separator": True,
                "items": [
                    {
                        "title": "Users",
                        "icon": "people",
                        "link": "/mondmin/auth/user/",
                    },
                ],
            },
        ],
    },
}
