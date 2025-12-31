

from django.db import models
from django.contrib.auth.models import User
from django.db.models import Q, F, CheckConstraint, UniqueConstraint

# 1. Core User and Relationship Models

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    profile_picture_url = models.URLField(max_length=500, blank=True)
    bio = models.TextField(blank=True)

    def __str__(self):
        return self.user.username

class UserPresence(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    is_online = models.BooleanField(default=False)
    last_seen = models.DateTimeField(auto_now=True)
    device_info = models.TextField(blank=True)

    def __str__(self):
        return f"{self.user.username} - {'Online' if self.is_online else 'Offline'}"

class Friendship(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        ACCEPTED = 'accepted', 'Accepted'

    user_one = models.ForeignKey(User, on_delete=models.CASCADE, related_name='friendships_one')
    user_two = models.ForeignKey(User, on_delete=models.CASCADE, related_name='friendships_two')
    requester = models.ForeignKey(User, on_delete=models.CASCADE, related_name='friend_requests_sent', null=True, blank=True)  # Allow NULL temporarily
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            CheckConstraint(check=Q(user_one_id__lt=F('user_two_id')), name='user_one_lt_user_two'),
            UniqueConstraint(fields=['user_one', 'user_two'], name='unique_friendship')
        ]

    def __str__(self):
        return f"{self.user_one.username} - {self.user_two.username} ({self.status})"


class BlockedUser(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blocking_users')
    blocked_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blocked_by_users')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'blocked_user')

    def __str__(self):
        return f"{self.user.username} blocked {self.blocked_user.username}"


# 2. Direct Messaging Models

class DirectChat(models.Model):
    user_one = models.ForeignKey(User, on_delete=models.CASCADE, related_name='direct_chats_one')
    user_two = models.ForeignKey(User, on_delete=models.CASCADE, related_name='direct_chats_two')
    created_at = models.DateTimeField(auto_now_add=True)
    last_message_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            CheckConstraint(check=Q(user_one_id__lt=F('user_two_id')), name='dm_user_one_lt_user_two'),
            UniqueConstraint(fields=['user_one', 'user_two'], name='unique_direct_chat')
        ]

    def __str__(self):
        return f"Chat between {self.user_one.username} and {self.user_two.username}"

class DirectMessage(models.Model):
    class MessageType(models.TextChoices):
        TEXT = 'text', 'Text'
        IMAGE = 'image', 'Image'
        FILE = 'file', 'File'
        AUDIO = 'audio', 'Audio'

    class DeliveryStatus(models.TextChoices):
        SENT = 'sent', 'Sent'
        DELIVERED = 'delivered', 'Delivered'
        SEEN = 'seen', 'Seen'

    chat = models.ForeignKey(DirectChat, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_direct_messages')
    message_text = models.TextField()
    message_type = models.CharField(max_length=10, choices=MessageType.choices, default=MessageType.TEXT)
    media_url = models.URLField(max_length=500, blank=True)
    delivery_status = models.CharField(max_length=10, choices=DeliveryStatus.choices, default=DeliveryStatus.SENT)
    edited_at = models.DateTimeField(blank=True, null=True)
    is_deleted_for_sender = models.BooleanField(default=False)
    is_deleted_for_receiver = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']


# 3. Group Chat Models

class Group(models.Model):
    class GroupType(models.TextChoices):
        PUBLIC = 'public', 'Public'
        PRIVATE = 'private', 'Private'
        LOCKED = 'locked', 'Locked'

    group_name = models.CharField(max_length=100)
    group_description = models.TextField(blank=True)
    group_avatar_url = models.URLField(max_length=500, blank=True)
    group_type = models.CharField(max_length=10, choices=GroupType.choices, default=GroupType.PRIVATE)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_groups')
    created_at = models.DateTimeField(auto_now_add=True)
    # --- THIS IS THE CORRECTED LINE ---
    members = models.ManyToManyField(User, through='GroupMember', through_fields=('group', 'user'), related_name='chat_groups')

    def __str__(self):
        return self.group_name

class GroupMessage(models.Model):
    MessageType = DirectMessage.MessageType

    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='sent_group_messages')
    message_text = models.TextField()
    message_type = models.CharField(max_length=10, choices=MessageType.choices, default=MessageType.TEXT)
    media_url = models.URLField(max_length=500, blank=True)
    edited_at = models.DateTimeField(blank=True, null=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

class GroupMember(models.Model):
    class Role(models.TextChoices):
        ADMIN = 'admin', 'Admin'
        MEMBER = 'member', 'Member'

    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.MEMBER)
    added_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='added_group_members')
    is_muted = models.BooleanField(default=False)
    last_read_message = models.ForeignKey(GroupMessage, on_delete=models.SET_NULL, null=True, blank=True)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('group', 'user')

    def __str__(self):
        return f"{self.user.username} in {self.group.group_name} ({self.role})"


# 4. Message Interaction Models

class DirectMessageReaction(models.Model):
    message = models.ForeignKey(DirectMessage, on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='direct_message_reactions')
    reaction_type = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('message', 'user', 'reaction_type')

class GroupMessageReaction(models.Model):
    message = models.ForeignKey(GroupMessage, on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='group_message_reactions')
    reaction_type = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('message', 'user', 'reaction_type')

