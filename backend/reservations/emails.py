import json
import logging
from io import BytesIO
from typing import Any

import qrcode
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas as rl_canvas

from reservations.models import Payment, Reservation

logger = logging.getLogger(__name__)


def _make_qr_buffer(data: dict[str, Any]) -> BytesIO:
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(json.dumps(data))
    qr.make(fit=True)
    buffer = BytesIO()
    qr.make_image(fill_color="black", back_color="white").save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


def _build_tickets_pdf(reservation: Reservation, tickets: list[tuple[str, BytesIO]]) -> BytesIO:
    event = reservation.event
    if event is None:
        raise ValueError("Reservation has no event to build tickets for")
    show = event.show
    if show is None:
        raise ValueError("Event has no show to build tickets for")
    pdf_buffer = BytesIO()
    width, height = A4
    canvas = rl_canvas.Canvas(pdf_buffer, pagesize=A4)
    center_x = width / 2

    for name, qr_buffer in tickets:
        qr_image = ImageReader(qr_buffer)
        qr_size = 220
        qr_x = (width - qr_size) / 2
        qr_y = height / 2 - qr_size / 2 + 20

        canvas.setFont("Helvetica-Bold", 22)
        canvas.drawCentredString(center_x, qr_y + qr_size + 60, show.title)

        canvas.setFont("Helvetica", 14)
        canvas.drawCentredString(
            center_x, qr_y + qr_size + 36, f"Ticket fuer / Ticket for:  {name}"
        )

        canvas.setLineWidth(0.5)
        canvas.line(72, qr_y + qr_size + 22, width - 72, qr_y + qr_size + 22)

        canvas.drawImage(qr_image, qr_x, qr_y, width=qr_size, height=qr_size)

        canvas.line(72, qr_y - 16, width - 72, qr_y - 16)

        canvas.setFont("Helvetica-Bold", 13)
        canvas.drawCentredString(center_x, qr_y - 36, event.date_str())

        canvas.setFont("Helvetica", 12)
        canvas.drawCentredString(
            center_x,
            qr_y - 54,
            f"Einlass {event.admission_time()}  ·  Beginn {event.show_time()}",
        )
        canvas.drawCentredString(
            center_x,
            qr_y - 72,
            "Bitte QR-Code an der Tuer vorzeigen  ·  Please show QR code at the door",
        )

        canvas.showPage()

    canvas.save()
    pdf_buffer.seek(0)
    return pdf_buffer


def send_confirmation_mail(reservation: Reservation) -> None:
    logger.info(
        "send_confirmation_mail: reservation=%s event=%s email=%s tickets=%s",
        reservation.id,
        reservation.event,
        reservation.email,
        reservation.ticket_count(),
    )
    event = reservation.event
    if event is None:
        raise ValueError("Reservation has no event to send a confirmation mail for")
    show = event.show
    if show is None:
        raise ValueError("Event has no show to send a confirmation mail for")
    guests = list(reservation.guests.all())
    payment = Payment.objects.filter(reservation=reservation).order_by("-created_at").first()

    tickets = [
        (
            f"{reservation.first_name} {reservation.last_name}",
            _make_qr_buffer({"ticket": str(reservation.id), "event": event.id}),
        )
    ]
    for guest in guests:
        if guest.ticket_id is None:
            continue
        tickets.append(
            (
                f"{guest.first_name} {guest.last_name}",
                _make_qr_buffer({"ticket": str(guest.ticket_id), "event": event.id}),
            )
        )

    pdf_buffer = _build_tickets_pdf(reservation, tickets)

    guests_de = ""
    guests_en = ""
    if guests:
        guest_names = "\n".join(f"  - {guest.first_name} {guest.last_name}" for guest in guests)
        guests_de = f"\nGaeste:\n{guest_names}\n"
        guests_en = f"\nGuests:\n{guest_names}\n"

    payment_de = ""
    payment_en = ""
    if payment:
        ticket_price = payment.ticket_price
        total = payment.total
        payment_de = f"\nPreis pro Ticket: {ticket_price:.2f} EUR\nGesamtbetrag: {total:.2f} EUR\n"
        payment_en = f"\nPrice per ticket: {ticket_price:.2f} EUR\nTotal paid: {total:.2f} EUR\n"

    body = f"""Liebe*r {reservation.first_name},
vielen Dank fuer deine Buchung fuer {show.title} am {event.date_str()}!

Deine Reservierung:
Name: {reservation.first_name} {reservation.last_name}
Reservierungs-ID: {reservation.id}
Tickets: {reservation.ticket_count()}{guests_de}{payment_de}
Im Anhang findest du das PDF mit deinen Tickets - fuer jede Person gibt es einen eigenen QR-Code. Falls ihr nicht gemeinsam ankommt, leite bitte den jeweiligen QR-Code an deine Gaeste weiter.

Wir oeffnen unsere Tore um {event.admission_time()}, die Show beginnt um {event.show_time()}.

Adresse: Rudolfstr. 14c, 10245 Berlin

Und falls du nicht nur Lust auf Zirkus, sondern auch auf Code hast: Die Website von Zirkus Mond ist auf GitHub oeffentlich einsehbar. Wenn du Fehler findest, Ideen hast oder ein wenig digitalen Glitzer beisteuern moechtest, freuen wir uns sehr ueber deinen Beitrag:
https://github.com/zirkusmond/zirkusmond

Wir freuen uns auf dich im Zirkus Mond - viel Spass!

Bitte beachte, dass Tickets nicht erstattungsfaehig sind. Falls du verhindert bist, kannst du dein Ticket gerne an jemand anderen weitergeben - gib einfach den QR-Code weiter.

------------------------------------------------------------

Dear {reservation.first_name},
thank you for your booking to {show.title} on the {event.date_str()}!

Your reservation:
Name: {reservation.first_name} {reservation.last_name}
Reservation ID: {reservation.id}
Tickets: {reservation.ticket_count()}{guests_en}{payment_en}
The attached PDF contains a individual QR code for each person in your booking. If you're not arriving together, please forward the relevant QR code to your guests.

We open our gates at {event.admission_time()}, the Show will start at {event.show_time()}.

Address: Rudolfstr. 14c, 10245 Berlin

And if you are not only into circus but also into code: the Zirkus Mond website is public on GitHub. If you spot a bug, have an idea, or want to sprinkle in a little digital glitter, we would love your contribution:
https://github.com/zirkusmond/zirkusmond

See you at Zirkus Mond and have fun!

Please note that tickets are non-refundable. However, if you can't make it, you're welcome to pass your ticket on to someone else - just forward the QR code.
"""

    email = EmailMultiAlternatives(
        subject=f"Zirkusmond - Thank you for your Reservation for {show.title}",
        body=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[reservation.email],
    )
    email.attach(f"tickets_{reservation.id}.pdf", pdf_buffer.read(), "application/pdf")
    email.send()
    logger.info("confirmation email delivered for reservation=%s", reservation.id)


def send_refund_mail(reservation: Reservation) -> None:
    logger.info(
        "send_refund_mail: reservation=%s event=%s email=%s",
        reservation.id,
        reservation.event,
        reservation.email,
    )
    event = reservation.event
    if event is None:
        raise ValueError("Reservation has no event to send a refund mail for")
    show = event.show
    if show is None:
        raise ValueError("Event has no show to send a refund mail for")
    payment = Payment.objects.filter(reservation=reservation).order_by("-created_at").first()

    payment_de = ""
    payment_en = ""
    if payment:
        total = payment.total
        payment_de = f"\nErstatteter Betrag: {total:.2f} EUR\n"
        payment_en = f"\nRefunded amount: {total:.2f} EUR\n"

    body = f"""Liebe*r {reservation.first_name},
deine Zahlung fuer {show.title} am {event.date_str()} wurde vollstaendig erstattet.

Details:
Reservierungs-ID: {reservation.id}{payment_de}
Der erstattete Betrag sollte innerhalb von 5-10 Werktagen auf deinem Konto erscheinen, abhaengig von deiner Bank.

Falls du Fragen hast, kontaktiere uns gerne.

Mit freundlichen Gruessen,
Das Zirkus Mond Team
------------------------------------------------------------

Dear {reservation.first_name},
your payment for {show.title} on the {event.date_str()} has been fully refunded.

Details:
Reservation ID: {reservation.id}{payment_en}
The refunded amount should appear in your account within 5-10 business days, depending on your bank.

If you have any questions, please feel free to contact us.

Best regards,
The Zirkus Mond Team
"""

    email = EmailMultiAlternatives(
        subject=f"Zirkusmond - Payment Refunded for {show.title}",
        body=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[reservation.email],
    )
    email.send()
    logger.info("refund email delivered for reservation=%s", reservation.id)
