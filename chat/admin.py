from django.contrib import admin
from .models import DirectMessage, DirectChat

@admin.register(DirectMessage)
class DirectMessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'chat', 'sender', 'message_text', 'created_at']
    list_filter = ['chat', 'sender', 'created_at']
    search_fields = ['message_text']
    ordering = ['-created_at']

@admin.register(DirectChat)
class DirectChatAdmin(admin.ModelAdmin):
    list_display = ['id', 'user_one', 'user_two', 'created_at', 'last_message_at']
