# chat/permissions.py

from rest_framework import permissions
from .models import GroupMember

class IsGroupAdmin(permissions.BasePermission):
    """
    Allows access only to admin members of a group.
    """
    def has_object_permission(self, request, view, obj):
        try:
            member = GroupMember.objects.get(group=obj, user=request.user)
            return member.role == GroupMember.Role.ADMIN
        except GroupMember.DoesNotExist:
            return False
