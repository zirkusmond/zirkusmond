import shutil
import tempfile
from datetime import timedelta
from io import BytesIO
from typing import Any

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone
from PIL import Image

from events.models import Event
from shows.image_processor import process_show_image
from shows.models import PastShow, Show, UnscheduledShow, UpcomingShow

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_image() -> SimpleUploadedFile:
    buf = BytesIO()
    Image.new("RGB", (10, 10), color="red").save(buf, format="JPEG")
    buf.seek(0)
    return SimpleUploadedFile("test.jpg", buf.read(), content_type="image/jpeg")


def make_banner_image() -> SimpleUploadedFile:
    buf = BytesIO()
    Image.new("RGB", (400, 225), color="blue").save(buf, format="JPEG")
    buf.seek(0)
    return SimpleUploadedFile("banner.jpg", buf.read(), content_type="image/jpeg")


def make_show(**kwargs: Any) -> Show:
    defaults = dict(
        title="Test Show",
        description="A description",
        cast="A cast",
        card_image=make_image(),
        banner_image=make_banner_image(),
        private=False,
    )
    defaults.update(kwargs)
    return Show.objects.create(**defaults)


def make_event(show: Show, offset_days: int = 7) -> Event:
    base = timezone.now() + timedelta(days=offset_days)
    return Event.objects.create(
        show=show,
        admission=base.replace(hour=19, minute=0, second=0, microsecond=0),
        begin=base.replace(hour=20, minute=0, second=0, microsecond=0),
        reservation_capacity=150,
        open_for_reservation=True,
    )


# ---------------------------------------------------------------------------
# Show model
# ---------------------------------------------------------------------------


class ShowModelTest(TestCase):
    def setUp(self) -> None:
        self.show = make_show()

    def test_str_is_title(self) -> None:
        self.assertEqual(str(self.show), "Test Show")

    def test_future_events_returns_upcoming(self) -> None:
        event = make_event(self.show, offset_days=5)
        self.assertIn(event, self.show.future_events())

    def test_future_events_excludes_past(self) -> None:
        past = make_event(self.show, offset_days=-1)
        self.assertNotIn(past, self.show.future_events())

    def test_last_event_returns_latest(self) -> None:
        make_event(self.show, offset_days=3)
        later = make_event(self.show, offset_days=10)
        self.assertEqual(self.show.last_event(), later)

    def test_first_event_returns_earliest(self) -> None:
        earlier = make_event(self.show, offset_days=3)
        make_event(self.show, offset_days=10)
        self.assertEqual(self.show.first_event(), earlier)

    def test_reservation_open_true_when_event_open(self) -> None:
        make_event(self.show)
        self.assertTrue(self.show.reservation_open())

    def test_reservation_open_false_with_no_events(self) -> None:
        self.assertFalse(self.show.reservation_open())

    def test_reservation_open_false_when_all_closed(self) -> None:
        make_event(self.show, offset_days=-1)
        self.assertFalse(self.show.reservation_open())

    def test_show_in_preview_true_for_public_with_future_event(self) -> None:
        make_event(self.show)
        self.assertTrue(self.show.show_in_preview())

    def test_show_in_preview_false_for_private_show(self) -> None:
        self.show.private = True
        self.show.save()
        make_event(self.show)
        self.assertFalse(self.show.show_in_preview())

    def test_show_in_preview_true_for_public_with_no_events(self) -> None:
        self.assertTrue(self.show.show_in_preview())

    def test_show_in_preview_false_when_last_event_long_past(self) -> None:
        make_event(self.show, offset_days=-2)
        self.assertFalse(self.show.show_in_preview())

    def test_dates_text_joins_future_events(self) -> None:
        make_event(self.show, offset_days=3)
        make_event(self.show, offset_days=10)
        result = self.show.dates_text()
        self.assertIn("/", result)

    def test_dates_text_empty_when_no_future_events(self) -> None:
        self.assertEqual(self.show.dates_text(), "")

    def test_lastmod_format(self) -> None:
        self.assertRegex(self.show.lastmod(), r"\d{4}-\d{2}-\d{2}")

    def test_sold_out_true_with_no_events(self) -> None:
        # Show with no events is considered sold out (no tickets available)
        self.assertTrue(self.show.sold_out())

    def test_sold_out_false_when_events_not_sold_out(self) -> None:
        make_event(self.show)
        self.assertFalse(self.show.sold_out())

    def test_sold_out_true_when_all_future_events_sold_out(self) -> None:
        from reservations.models import Payment, Reservation

        # Create two future events, both at capacity
        event1 = Event.objects.create(
            show=self.show,
            admission=timezone.now() + timedelta(days=5),
            begin=timezone.now() + timedelta(days=5, hours=1),
            reservation_capacity=1,
            open_for_reservation=True,
        )
        event2 = Event.objects.create(
            show=self.show,
            admission=timezone.now() + timedelta(days=10),
            begin=timezone.now() + timedelta(days=10, hours=1),
            reservation_capacity=1,
            open_for_reservation=True,
        )

        # Fill both events over capacity
        for event in [event1, event2]:
            res1 = Reservation.objects.create(
                event=event, first_name="A", last_name="B", email=f"a{event.id}@example.com"
            )
            Payment.objects.create(
                reservation=res1, total=15, custom_ticket_price=15, status=Payment.Status.COMPLETED
            )
            res2 = Reservation.objects.create(
                event=event, first_name="C", last_name="D", email=f"c{event.id}@example.com"
            )
            Payment.objects.create(
                reservation=res2, total=15, custom_ticket_price=15, status=Payment.Status.COMPLETED
            )

        self.assertTrue(self.show.sold_out())

    def test_sold_out_false_when_some_events_not_sold_out(self) -> None:
        from reservations.models import Payment, Reservation

        # Create two events: one sold out, one not
        sold_out_event = Event.objects.create(
            show=self.show,
            admission=timezone.now() + timedelta(days=5),
            begin=timezone.now() + timedelta(days=5, hours=1),
            reservation_capacity=1,
            open_for_reservation=True,
        )
        Event.objects.create(
            show=self.show,
            admission=timezone.now() + timedelta(days=10),
            begin=timezone.now() + timedelta(days=10, hours=1),
            reservation_capacity=10,
            open_for_reservation=True,
        )

        # Fill the first event over capacity
        res1 = Reservation.objects.create(
            event=sold_out_event, first_name="A", last_name="B", email="a@example.com"
        )
        Payment.objects.create(
            reservation=res1, total=15, custom_ticket_price=15, status=Payment.Status.COMPLETED
        )
        res2 = Reservation.objects.create(
            event=sold_out_event, first_name="C", last_name="D", email="c@example.com"
        )
        Payment.objects.create(
            reservation=res2, total=15, custom_ticket_price=15, status=Payment.Status.COMPLETED
        )

        # Show should not be sold out if one event has availability
        self.assertFalse(self.show.sold_out())


# ---------------------------------------------------------------------------
# Show managers
# ---------------------------------------------------------------------------


class ShowManagerTest(TestCase):
    def setUp(self) -> None:
        self.upcoming_show = make_show(title="Upcoming")
        make_event(self.upcoming_show, offset_days=5)

        self.past_show = make_show(title="Past")
        make_event(self.past_show, offset_days=-5)

        self.unscheduled_show = make_show(title="Unscheduled")

    def test_upcoming_includes_shows_with_future_events(self) -> None:
        self.assertIn(self.upcoming_show, UpcomingShow.objects.all())

    def test_upcoming_excludes_past_only_shows(self) -> None:
        self.assertNotIn(self.past_show, UpcomingShow.objects.all())

    def test_upcoming_excludes_unscheduled(self) -> None:
        self.assertNotIn(self.unscheduled_show, UpcomingShow.objects.all())

    def test_past_includes_shows_with_only_past_events(self) -> None:
        self.assertIn(self.past_show, PastShow.objects.all())

    def test_past_excludes_upcoming(self) -> None:
        self.assertNotIn(self.upcoming_show, PastShow.objects.all())

    def test_unscheduled_includes_shows_with_no_events(self) -> None:
        self.assertIn(self.unscheduled_show, UnscheduledShow.objects.all())

    def test_unscheduled_excludes_shows_with_events(self) -> None:
        self.assertNotIn(self.upcoming_show, UnscheduledShow.objects.all())
        self.assertNotIn(self.past_show, UnscheduledShow.objects.all())


# ---------------------------------------------------------------------------
# Site-wide views
# ---------------------------------------------------------------------------


class SiteViewsTest(TestCase):
    def test_home_returns_200(self) -> None:
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

    def test_home_with_upcoming_show(self) -> None:
        show = make_show()
        make_event(show)
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("upcoming_shows", data)
        self.assertEqual(len(data["upcoming_shows"]), 1)
        self.assertEqual(data["upcoming_shows"][0]["title"], "Test Show")

    def test_home_limits_to_six_shows(self) -> None:
        """Homepage should only return 6 shows even if more exist."""
        for i in range(10):
            show = make_show(title=f"Show {i}")
            make_event(show, offset_days=i + 1)
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["upcoming_shows"]), 6)

    def test_all_shows_returns_all(self) -> None:
        """The /shows/ endpoint should return all upcoming shows."""
        for i in range(10):
            show = make_show(title=f"Show {i}")
            make_event(show, offset_days=i + 1)
        response = self.client.get("/shows/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["upcoming_shows"]), 10)

    def test_all_shows_excludes_private(self) -> None:
        """Private shows should not appear in /shows/."""
        public_show = make_show(title="Public", private=False)
        private_show = make_show(title="Private", private=True)
        make_event(public_show)
        make_event(private_show)
        response = self.client.get("/shows/")
        data = response.json()
        titles = [s["title"] for s in data["upcoming_shows"]]
        self.assertIn("Public", titles)
        self.assertNotIn("Private", titles)


# ---------------------------------------------------------------------------
# Image processing
# ---------------------------------------------------------------------------


def make_jpeg_bytes(width: int, height: int) -> BytesIO:
    buf = BytesIO()
    Image.new("RGB", (width, height), color="green").save(buf, format="JPEG")
    buf.seek(0)
    return buf


def make_jpeg_upload(width: int, height: int, name: str = "pic.jpg") -> SimpleUploadedFile:
    return SimpleUploadedFile(
        name, make_jpeg_bytes(width, height).read(), content_type="image/jpeg"
    )


class ProcessShowImageTest(TestCase):
    def test_returns_webp(self) -> None:
        result = process_show_image(make_jpeg_bytes(800, 800), max_width=900)
        self.assertEqual(Image.open(result).format, "WEBP")

    def test_crops_wide_image_to_square(self) -> None:
        result = process_show_image(make_jpeg_bytes(800, 400), max_width=900)
        img = Image.open(result)
        self.assertEqual(img.width, img.height)
        self.assertEqual(img.width, 400)

    def test_crops_tall_image_to_square(self) -> None:
        result = process_show_image(make_jpeg_bytes(400, 800), max_width=900)
        img = Image.open(result)
        self.assertEqual(img.width, img.height)
        self.assertEqual(img.width, 400)

    def test_resizes_down_to_max_width(self) -> None:
        result = process_show_image(make_jpeg_bytes(2000, 2000), max_width=900)
        img = Image.open(result)
        self.assertEqual(img.width, 900)
        self.assertEqual(img.height, 900)

    def test_does_not_upscale_below_max_width(self) -> None:
        result = process_show_image(make_jpeg_bytes(300, 300), max_width=900)
        self.assertEqual(Image.open(result).width, 300)

    def test_crop_false_preserves_aspect_ratio(self) -> None:
        result = process_show_image(make_jpeg_bytes(1600, 900), max_width=1600, crop=False)
        img = Image.open(result)
        self.assertEqual((img.width, img.height), (1600, 900))

    def test_crop_false_still_resizes_down(self) -> None:
        result = process_show_image(make_jpeg_bytes(2000, 1000), max_width=1600, crop=False)
        img = Image.open(result)
        self.assertEqual((img.width, img.height), (1600, 800))


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class ShowSaveImageProcessingTest(TestCase):
    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def make_show(self, **kwargs: Any) -> Show:
        defaults = dict(
            title="Image Show",
            description="A description",
            cast="A cast",
            card_image=make_jpeg_upload(800, 400, name="card.jpg"),
            banner_image=make_jpeg_upload(2000, 1000, name="banner.jpg"),
            private=False,
        )
        defaults.update(kwargs)
        return Show.objects.create(**defaults)

    def test_card_image_converted_to_webp(self) -> None:
        show = self.make_show()
        self.assertTrue(show.card_image.name.endswith(".webp"))
        self.assertEqual(Image.open(show.card_image).format, "WEBP")

    def test_banner_image_converted_to_webp(self) -> None:
        show = self.make_show()
        self.assertTrue(show.banner_image.name.endswith(".webp"))
        self.assertEqual(Image.open(show.banner_image).format, "WEBP")

    def test_card_image_cropped_square_and_capped_at_max_width(self) -> None:
        show = self.make_show(card_image=make_jpeg_upload(3000, 3000, name="big.jpg"))
        img = Image.open(show.card_image)
        self.assertEqual(img.width, img.height)
        self.assertEqual(img.width, Show.CARD_IMAGE_MAX_WIDTH)

    def test_banner_image_not_cropped_to_square(self) -> None:
        show = self.make_show()
        img = Image.open(show.banner_image)
        self.assertEqual((img.width, img.height), (1600, 800))

    def test_save_without_banner_image(self) -> None:
        show = self.make_show(banner_image="")
        self.assertFalse(show.banner_image)
        self.assertTrue(show.card_image.name.endswith(".webp"))

    def test_reprocessing_is_skipped_for_existing_webp(self) -> None:
        show = self.make_show()
        processed_name = show.card_image.name
        show.title = "Renamed"
        show.save()
        show.refresh_from_db()
        self.assertEqual(show.card_image.name, processed_name)
