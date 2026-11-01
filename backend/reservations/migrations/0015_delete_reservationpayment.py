from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("reservations", "0014_alter_payment_created_at"),
    ]

    operations = [
        migrations.DeleteModel(
            name="ReservationPayment",
        ),
    ]
