from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response

from .models import TeamMember
from .serializers import TeamMemberSerializer


@api_view(["GET"])
def all_team_members(request: Request) -> Response:
    team_members = TeamMember.objects.all()
    serializer = TeamMemberSerializer(team_members, many=True, context={"request": request})
    return Response({"team_members": serializer.data})
