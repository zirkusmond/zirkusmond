from django.db import models


class TeamMember(models.Model):
    name = models.CharField(max_length=255)
    role_de = models.CharField(max_length=255, verbose_name="Role (German)", default="")
    role_en = models.CharField(max_length=255, verbose_name="Role (English)", default="")
    image = models.ImageField(upload_to="team/")
    order = models.IntegerField(default=0, help_text="Display order (lower numbers appear first)")
    last_modified = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self) -> str:
        return self.name
