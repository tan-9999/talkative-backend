# chat/urls.py

from django.urls import path
from . import views
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    # Auth & Profile
    path('auth/register/', views.RegisterView.as_view(), name='register'),
    path('auth/login/', views.LoginView.as_view(), name='login'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/me/', views.CurrentUserView.as_view(), name='current_user'),
    path('profile/', views.ProfileDetailView.as_view(), name='profile-detail'),

    # Friendships
    path('friendships/', views.FriendshipListView.as_view(), name='friendship-list'),
    path('friendships/<int:pk>/', views.FriendshipDetailView.as_view(), name='friendship-detail'),

    # Groups and Members
    path('groups/', views.GroupListView.as_view(), name='group-list'),
    path('groups/<int:pk>/', views.GroupDetailView.as_view(), name='group-detail'),
    path('groups/<int:pk>/members/', views.GroupMemberView.as_view(), name='group-members'),

    # Direct Chats
    path('direct-chats/', views.DirectChatListView.as_view(), name='direct-chat-list'),
    path('direct-chats/<int:user_id>/', views.DirectChatDetailView.as_view(), name='direct-chat-detail'),
    
    # Messages
    path('chats/<int:chat_id>/messages/', views.DirectMessageListView.as_view(), name='chat-messages'),
    
    # Search Users
    path('users/search/', views.UserSearchView.as_view(), name='user-search'),
]
