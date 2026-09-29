from rest_framework.serializers import ModelSerializer

from .models import TeamMember


class TeamMemberSerializer(ModelSerializer):
    class Meta:
        model = TeamMember
        fields = ["id", "name", "role_de", "role_en", "image", "order"]
