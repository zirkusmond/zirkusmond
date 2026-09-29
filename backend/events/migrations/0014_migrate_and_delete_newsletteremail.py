from django.db import migrations


def copy_newsletter_emails(apps, schema_editor):
    NewsletterEmail = apps.get_model("events", "NewsletterEmail")
    NewsletterSubscription = apps.get_model("newsletter", "NewsletterSubscription")

    existing = set(NewsletterSubscription.objects.values_list("email", flat=True))
    to_create = [
        NewsletterSubscription(email=obj.email)
        for obj in NewsletterEmail.objects.all()
        if obj.email not in existing
    ]
    NewsletterSubscription.objects.bulk_create(to_create)


class Migration(migrations.Migration):
    dependencies = [
        ("events", "0013_guest_checked_in_guest_ticket_id"),
        ("newsletter", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(copy_newsletter_emails, migrations.RunPython.noop),
        migrations.DeleteModel(name="NewsletterEmail"),
    ]
