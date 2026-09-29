import os
import shutil
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from team_members.models import TeamMember


class Command(BaseCommand):
    help = "Seeds the database with the main team members"

    def handle(self, *args, **options):
        # Define the team members data matching the original hardcoded list
        team_data = [
            {
                "name": "Max & Marlen",
                "role_de": "Zirkus Leitung",
                "role_en": "Circus Directors",
                "image_source": "MnM.webp",
                "order": 1,
            },
            {
                "name": "Juan",
                "role_de": "Künstlerische Leitung",
                "role_en": "Artistic Director",
                "image_source": "img-6.webp",  # from gallery
                "order": 2,
            },
            {
                "name": "Maria",
                "role_de": "Produktionsleitung",
                "role_en": "Head of Productions",
                "image_source": "maria.webp",
                "order": 3,
            },
            {
                "name": "Valerio",
                "role_de": "Techniker",
                "role_en": "Technician",
                "image_source": "valerio.webp",
                "order": 4,
            },
            {
                "name": "Philo & Alex",
                "role_de": "IT",
                "role_en": "IT",
                "image_source": "philo_alex.jpg",
                "order": 5,
            },
        ]

        # Ensure the team media directory exists
        team_media_dir = Path(settings.MEDIA_ROOT) / "team"
        team_media_dir.mkdir(parents=True, exist_ok=True)

        for member_data in team_data:
            # Check if this team member already exists
            existing_member = TeamMember.objects.filter(name=member_data["name"]).first()

            if existing_member:
                self.stdout.write(
                    self.style.WARNING(f"Team member '{member_data['name']}' already exists")
                )
                continue

            # Determine source path for the image
            image_source = member_data["image_source"]
            source_path = None

            if image_source == "img-6.webp":
                # This image is in the gallery folder
                # Try media/gallery first (production), then frontend public (development)
                media_gallery_path = Path(settings.MEDIA_ROOT) / "gallery" / image_source
                frontend_gallery_path = (
                    Path(settings.BASE_DIR).parent
                    / "frontend"
                    / "public"
                    / "images"
                    / "gallery"
                    / image_source
                )
                source_path = (
                    media_gallery_path if media_gallery_path.exists() else frontend_gallery_path
                )
            else:
                # Try to find the image in the frontend public directory
                # This assumes the command is run in development where frontend is accessible
                frontend_team_path = (
                    Path(settings.BASE_DIR).parent
                    / "frontend"
                    / "public"
                    / "images"
                    / "team"
                    / image_source
                )
                source_path = frontend_team_path

            # Destination path in media/team/
            dest_filename = image_source
            dest_path = team_media_dir / dest_filename

            # Copy the image if source exists
            if source_path.exists():
                if not dest_path.exists():
                    shutil.copy2(source_path, dest_path)
                    self.stdout.write(self.style.SUCCESS(f"Copied image: {image_source}"))
                else:
                    self.stdout.write(f"Image already exists: {image_source}")
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f"Source image not found: {source_path}. "
                        f"You'll need to upload it manually for {member_data['name']}"
                    )
                )

            # Create the team member
            TeamMember.objects.create(
                name=member_data["name"],
                role_de=member_data["role_de"],
                role_en=member_data["role_en"],
                image=f"team/{dest_filename}",
                order=member_data["order"],
            )
            self.stdout.write(self.style.SUCCESS(f"Created team member: {member_data['name']}"))

        self.stdout.write(self.style.SUCCESS("Team members seeding completed!"))
