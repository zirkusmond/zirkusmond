import shutil
import tempfile
from io import BytesIO
from pathlib import Path
from typing import Any

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from PIL import Image
from rest_framework.test import APIClient

from team_members.models import TeamMember

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_image() -> SimpleUploadedFile:
    buf = BytesIO()
    Image.new("RGB", (10, 10), color="red").save(buf, format="JPEG")
    buf.seek(0)
    return SimpleUploadedFile("test.jpg", buf.read(), content_type="image/jpeg")


def make_team_member(**kwargs: Any) -> TeamMember:
    defaults = dict(
        name="Test Member",
        role_de="Test Role DE",
        role_en="Test Role EN",
        image=make_image(),
        order=0,
    )
    defaults.update(kwargs)
    return TeamMember.objects.create(**defaults)


# ---------------------------------------------------------------------------
# TeamMember model
# ---------------------------------------------------------------------------


class TeamMemberModelTest(TestCase):
    def test_create_team_member(self):
        member = make_team_member(
            name="John Doe", role_de="Entwickler", role_en="Developer", order=1
        )
        self.assertEqual(member.name, "John Doe")
        self.assertEqual(member.role_de, "Entwickler")
        self.assertEqual(member.role_en, "Developer")
        self.assertEqual(member.order, 1)
        self.assertIsNotNone(member.image)
        self.assertIsNotNone(member.last_modified)

    def test_str_representation(self):
        member = make_team_member(name="Jane Smith")
        self.assertEqual(str(member), "Jane Smith")

    def test_ordering(self):
        member1 = make_team_member(name="Alice", order=2)
        member2 = make_team_member(name="Bob", order=1)
        member3 = make_team_member(name="Charlie", order=1)

        members = list(TeamMember.objects.all())
        # Should order by order field first, then by name
        self.assertEqual(members[0].name, "Bob")
        self.assertEqual(members[1].name, "Charlie")
        self.assertEqual(members[2].name, "Alice")


# ---------------------------------------------------------------------------
# API endpoint
# ---------------------------------------------------------------------------


class TeamMemberAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_get_all_team_members_empty(self):
        response = self.client.get("/team-members/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"team_members": []})

    def test_get_all_team_members(self):
        member1 = make_team_member(
            name="Alice", role_de="Entwicklerin", role_en="Developer", order=1
        )
        member2 = make_team_member(name="Bob", role_de="Designer", role_en="Designer", order=2)

        response = self.client.get("/team-members/")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(len(data["team_members"]), 2)

        # Check that members are returned in correct order
        self.assertEqual(data["team_members"][0]["name"], "Alice")
        self.assertEqual(data["team_members"][0]["role_de"], "Entwicklerin")
        self.assertEqual(data["team_members"][0]["role_en"], "Developer")
        self.assertEqual(data["team_members"][0]["order"], 1)

        self.assertEqual(data["team_members"][1]["name"], "Bob")
        self.assertEqual(data["team_members"][1]["role_de"], "Designer")
        self.assertEqual(data["team_members"][1]["role_en"], "Designer")
        self.assertEqual(data["team_members"][1]["order"], 2)

    def test_team_member_serialization(self):
        member = make_team_member(name="Test Person", role_de="Tester", role_en="Tester", order=5)

        response = self.client.get("/team-members/")
        data = response.json()

        member_data = data["team_members"][0]
        self.assertIn("id", member_data)
        self.assertIn("name", member_data)
        self.assertIn("role_de", member_data)
        self.assertIn("role_en", member_data)
        self.assertIn("image", member_data)
        self.assertIn("order", member_data)
        self.assertEqual(member_data["id"], member.id)


# ---------------------------------------------------------------------------
# Management command
# ---------------------------------------------------------------------------


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class SeedTeamMembersCommandTest(TestCase):
    def setUp(self):
        # Create a temporary frontend structure for testing
        self.test_media_root = Path(tempfile.mkdtemp())
        self.frontend_path = self.test_media_root / "frontend" / "public" / "images"
        self.frontend_team_path = self.frontend_path / "team"
        self.frontend_gallery_path = self.frontend_path / "gallery"

        self.frontend_team_path.mkdir(parents=True, exist_ok=True)
        self.frontend_gallery_path.mkdir(parents=True, exist_ok=True)

        # Create dummy images
        self._create_dummy_image(self.frontend_team_path / "MnM.webp")
        self._create_dummy_image(self.frontend_team_path / "maria.webp")
        self._create_dummy_image(self.frontend_team_path / "valerio.webp")
        self._create_dummy_image(self.frontend_team_path / "philo_alex.jpg")
        self._create_dummy_image(self.frontend_gallery_path / "img-6.webp")

    def _create_dummy_image(self, path: Path):
        img = Image.new("RGB", (10, 10), color="red")
        img.save(path)

    def tearDown(self):
        shutil.rmtree(self.test_media_root, ignore_errors=True)

    @override_settings(BASE_DIR=lambda: None)
    def test_seed_command_creates_team_members(self):
        # Mock BASE_DIR to point to our test structure
        with override_settings(BASE_DIR=self.test_media_root):
            self.assertEqual(TeamMember.objects.count(), 0)

            # Run the command
            call_command("seed_team_members")

            # Verify team members were created
            self.assertEqual(TeamMember.objects.count(), 5)

            # Verify specific members exist
            max_marlen = TeamMember.objects.get(name="Max & Marlen")
            self.assertEqual(max_marlen.order, 1)

            juan = TeamMember.objects.get(name="Juan")
            self.assertEqual(juan.order, 2)

    @override_settings(BASE_DIR=lambda: None)
    def test_seed_command_is_idempotent(self):
        with override_settings(BASE_DIR=self.test_media_root):
            # Run command twice
            call_command("seed_team_members")
            call_command("seed_team_members")

            # Should still only have 5 members
            self.assertEqual(TeamMember.objects.count(), 5)

    @override_settings(BASE_DIR=lambda: None)
    def test_seed_command_skips_existing_members(self):
        with override_settings(BASE_DIR=self.test_media_root):
            # Create one member manually
            make_team_member(
                name="Max & Marlen", role_de="Custom Role", role_en="Custom Role", order=10
            )

            call_command("seed_team_members")

            # Should have 5 total (1 existing + 4 new)
            self.assertEqual(TeamMember.objects.count(), 5)

            # Existing member should not be modified
            existing = TeamMember.objects.get(name="Max & Marlen")
            self.assertEqual(existing.role_de, "Custom Role")
            self.assertEqual(existing.order, 10)
