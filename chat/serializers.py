from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    Profile, UserPresence, Friendship, BlockedUser,
    DirectChat, DirectMessage, Group, GroupMember, GroupMessage,
    DirectMessageReaction, GroupMessageReaction
)


# --- User & Profile Serializers ---


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ['profile_picture_url', 'bio']


class UserSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'profile']


class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'email', 'password']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password']
        )
        Profile.objects.create(user=user)
        UserPresence.objects.create(user=user)
        return user


# --- Friendship & Blocking Serializers ---


class CreateFriendshipSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()


class FriendshipSerializer(serializers.ModelSerializer):
    user_one = UserSerializer(read_only=True)
    user_two = UserSerializer(read_only=True)
    requester = UserSerializer(read_only=True)

    class Meta:
        model = Friendship
        fields = ['id', 'user_one', 'user_two', 'requester', 'status', 'created_at']


# --- Direct Messaging Serializers ---


class DirectMessageSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)

    class Meta:
        model = DirectMessage
        fields = [
            'id', 'chat', 'sender', 'message_text', 'message_type',
            'media_url', 'delivery_status', 'created_at', 'edited_at'
        ]
        read_only_fields = ['id', 'chat', 'sender', 'created_at', 'edited_at', 'delivery_status']



class CreateMessageSerializer(serializers.Serializer):
    message_text = serializers.CharField()
    message_type = serializers.ChoiceField(
        choices=DirectMessage.MessageType.choices, 
        default=DirectMessage.MessageType.TEXT
    )
    media_url = serializers.URLField(required=False, allow_blank=True)


class DirectChatSerializer(serializers.ModelSerializer):
    user_one = UserSerializer(read_only=True)
    user_two = UserSerializer(read_only=True)
    messages = DirectMessageSerializer(many=True, read_only=True)

    class Meta:
        model = DirectChat
        fields = ['id', 'user_one', 'user_two', 'last_message_at', 'messages']


# --- Group Chat Serializers ---


class GroupMemberSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = GroupMember
        fields = ['user', 'role', 'joined_at']


class GroupSerializer(serializers.ModelSerializer):
    created_by = UserSerializer(read_only=True)
    members = GroupMemberSerializer(many=True, read_only=True, source='groupmember_set')

    class Meta:
        model = Group
        fields = [
            'id', 'group_name', 'group_description', 'group_avatar_url',
            'group_type', 'created_by', 'created_at', 'members'
        ]
        read_only_fields = ['created_by', 'created_at', 'members']


class AddGroupMemberSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    role = serializers.ChoiceField(choices=GroupMember.Role.choices, default=GroupMember.Role.MEMBER)
