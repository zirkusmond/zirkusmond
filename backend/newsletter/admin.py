from io import BytesIO

import xlsxwriter
from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse
from django.utils import timezone
from unfold.admin import ModelAdmin

from .models import NewsletterSubscription


class NewsletterSubscriptionAdmin(ModelAdmin):
    list_display = ("email", "created_at")
    actions = ["export_adresses"]

    @admin.action(description="Export EMail Adresses")
    def export_adresses(
        self, request: HttpRequest, queryset: QuerySet[NewsletterSubscription]
    ) -> HttpResponse:
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet()

        data = map(lambda x: x.email, queryset)
        worksheet.write_column(0, 0, data)

        workbook.close()
        xlsx_data = output.getvalue()
        filename = timezone.now().strftime("email_addresses_%Y_%m_%d.xlsx")
        response = HttpResponse(
            headers={
                "Content-Type": "application/vnd.ms-excel",
                "Content-Disposition": f"attachment; filename={filename}",
            }
        )
        response.write(xlsx_data)
        return response


admin.site.register(NewsletterSubscription, NewsletterSubscriptionAdmin)
