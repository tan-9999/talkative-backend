# chat/views.py

from django.db import models
from django.contrib.auth.models import User
from rest_framework import generics, status, permissions, filters
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework_simplejwt.tokens import RefreshToken
from .models import Profile, Friendship, DirectChat, DirectMessage, Group, GroupMember  
from .serializers import (
    RegisterSerializer, UserSerializer, ProfileSerializer, FriendshipSerializer,
    CreateFriendshipSerializer, DirectChatSerializer, DirectMessageSerializer, 
    CreateMessageSerializer, GroupSerializer, AddGroupMemberSerializer
)
from .permissions import IsGroupAdmin

# --- Authentication and Profile Views ---

class RegisterView(generics.CreateAPIView):
    # ... (no changes)
    queryset = User.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterSerializer

class LoginView(APIView):
    # ... (no changes)
    permission_classes = [permissions.AllowAny]
    def post(self, request, *args, **kwargs):
        username = request.data.get('username')
        password = request.data.get('password')
        try:
            user = User.objects.get(username=username)
            if user.check_password(password):
                refresh = RefreshToken.for_user(user)
                return Response({
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                    'user': UserSerializer(user).data
                })
            else:
                return Response({'error': 'Invalid credentials'}, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            return Response({'error': 'Invalid credentials'}, status=status.HTTP_400_BAD_REQUEST)

class CurrentUserView(generics.RetrieveAPIView):
    # ... (no changes)
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSerializer
    def get_object(self):
        return self.request.user

class ProfileDetailView(generics.RetrieveUpdateAPIView):
    """ View and update the profile of the currently authenticated user. """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ProfileSerializer
    queryset = Profile.objects.all()

    def get_object(self):
        # Ensures a user can only see/edit their own profile
        return self.request.user.profile

# --- Friendship Views ---

class FriendshipListView(generics.ListCreateAPIView):
    """ List friends or send a new friend request. """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = FriendshipSerializer

    def get_queryset(self):
        user = self.request.user
        # Return pending and accepted friendships
        return Friendship.objects.filter(models.Q(user_one=user) | models.Q(user_two=user))

    def perform_create(self, serializer):
        # Use a different serializer for creation
        create_serializer = CreateFriendshipSerializer(data=self.request.data)
        create_serializer.is_valid(raise_exception=True)
        target_user_id = create_serializer.validated_data['user_id']
        
        user = self.request.user
        if user.id == target_user_id:
            raise ValidationError("You cannot send a friend request to yourself.")

        try:
            target_user = User.objects.get(id=target_user_id)
        except User.DoesNotExist:
            raise ValidationError("Target user not found.")

        # Ensure IDs are ordered to prevent duplicate entries
        user1, user2 = sorted([user, target_user], key=lambda u: u.id)

        if Friendship.objects.filter(user_one=user1, user_two=user2).exists():
            raise ValidationError("A friendship or pending request already exists.")

        Friendship.objects.create(user_one=user1, user_two=user2, status=Friendship.Status.PENDING)

class FriendshipDetailView(generics.RetrieveUpdateDestroyAPIView):
    """ Accept, reject, or delete a friendship. """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = FriendshipSerializer
    queryset = Friendship.objects.all()

    def get_object(self):
        obj = super().get_object()
        # Ensure the current user is part of the friendship
        if self.request.user not in [obj.user_one, obj.user_two]:
            raise PermissionDenied()
        return obj

    def perform_update(self, serializer):
        friendship = self.get_object()
        current_user = self.request.user
        
        # DEBUG: Print values to console
        # print(f"DEBUG: Current user: {current_user.id} ({current_user.username})")
        # print(f"DEBUG: Friendship ID: {friendship.id}")
        # print(f"DEBUG: user_one: {friendship.user_one.id} ({friendship.user_one.username})")
        # print(f"DEBUG: user_two: {friendship.user_two.id} ({friendship.user_two.username})")
        # print(f"DEBUG: requester: {friendship.requester.id if friendship.requester else 'None'}")
        # print(f"DEBUG: status: {friendship.status}")
        
        # Only pending friendships can be accepted
        if friendship.status != Friendship.Status.PENDING:
            raise PermissionDenied("This friendship is already accepted.")
        
        # If requester is None (old data), allow anyone to accept
        if friendship.requester is None:
            # print("DEBUG: Requester is None, allowing accept")
            serializer.save(status=Friendship.Status.ACCEPTED)
            return
        
        # Determine who the receiver is (the person who didn't send the request)
        receiver = friendship.user_two if friendship.requester == friendship.user_one else friendship.user_one
        
        # print(f"DEBUG: Receiver (should accept): {receiver.id} ({receiver.username})")
        # print(f"DEBUG: Is current user the receiver? {current_user == receiver}")
        
        if current_user == receiver:
            serializer.save(status=Friendship.Status.ACCEPTED)
            # print("DEBUG: Request accepted successfully")
        else:
            raise PermissionDenied("You cannot accept your own friend request.")
            
    def perform_destroy(self, instance):
        # Either user can delete a friendship (pending or accepted)
        instance.delete()

# --- Group and Member Views ---

class GroupListView(generics.ListCreateAPIView):
    # ... (no changes)
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = GroupSerializer
    def get_queryset(self):
        return self.request.user.chat_groups.all()
    def perform_create(self, serializer):
        create_serializer = CreateFriendshipSerializer(data=self.request.data)
        create_serializer.is_valid(raise_exception=True)
        target_user_id = create_serializer.validated_data['user_id']
    
        user = self.request.user
        if user.id == target_user_id:
            raise ValidationError("You cannot send a friend request to yourself.")

        try:
            target_user = User.objects.get(id=target_user_id)
        except User.DoesNotExist:
            raise ValidationError("Target user not found.")

        # Ensure IDs are ordered to prevent duplicate entries
        user1, user2 = sorted([user, target_user], key=lambda u: u.id)

        if Friendship.objects.filter(user_one=user1, user_two=user2).exists():
            raise ValidationError("A friendship or pending request already exists.")

    # NEW: Store who sent the request
        Friendship.objects.create(
            user_one=user1, 
            user_two=user2, 
            requester=user,  # Track the sender
            status=Friendship.Status.PENDING
        )


class GroupDetailView(generics.RetrieveUpdateDestroyAPIView):
    """ View details, update, or delete a specific group. """
    permission_classes = [permissions.IsAuthenticated, IsGroupAdmin]
    serializer_class = GroupSerializer
    queryset = Group.objects.all()

class GroupMemberView(APIView):
    """ Add or remove a member from a group. """
    permission_classes = [permissions.IsAuthenticated, IsGroupAdmin]

    def post(self, request, pk):
        """ Add a member to a group. """
        serializer = AddGroupMemberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        group = generics.get_object_or_404(Group.objects.all(), pk=pk)
        self.check_object_permissions(request, group) # Check if user is admin

        try:
            user_to_add = User.objects.get(id=serializer.validated_data['user_id'])
        except User.DoesNotExist:
            raise ValidationError("User to add not found.")
            
        if group.members.filter(id=user_to_add.id).exists():
            raise ValidationError("User is already a member of this group.")

        GroupMember.objects.create(
            group=group,
            user=user_to_add,
            role=serializer.validated_data['role'],
            added_by=request.user
        )
        return Response({'status': 'member added'}, status=status.HTTP_201_CREATED)

    def delete(self, request, pk):
        """ Remove a member from a group. """
        serializer = AddGroupMemberSerializer(data=request.data) # Re-using for user_id validation
        serializer.is_valid(raise_exception=True)
        group = generics.get_object_or_404(Group.objects.all(), pk=pk)
        self.check_object_permissions(request, group)

        try:
            member_to_remove = GroupMember.objects.get(
                group=group,
                user_id=serializer.validated_data['user_id']
            )
        except GroupMember.DoesNotExist:
            raise ValidationError("This user is not a member of the group.")

        # Prevent removing the last admin if they are the one being removed
        if member_to_remove.role == GroupMember.Role.ADMIN and group.groupmember_set.filter(role=GroupMember.Role.ADMIN).count() == 1:
            raise ValidationError("Cannot remove the last admin from the group.")
            
        member_to_remove.delete()
        return Response({'status': 'member removed'}, status=status.HTTP_204_NO_CONTENT)


# --- Direct Chat Views ---
class DirectChatListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DirectChatSerializer

    def get_queryset(self):
        user = self.request.user
        return DirectChat.objects.filter(models.Q(user_one=user) | models.Q(user_two=user))
    
    
# --- Search Users View ---

class UserSearchView(generics.ListAPIView):
    """Search users by username or email to send friend requests."""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSerializer
    queryset = User.objects.all()
    filter_backends = [filters.SearchFilter]
    search_fields = ['username', 'email', 'profile__bio']
    
    def get_queryset(self):
        # Exclude the current user from search results
        return User.objects.exclude(id=self.request.user.id)
    
    

# Add these views at the end

class DirectChatDetailView(generics.RetrieveAPIView):
    """Get or create a direct chat between two users."""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DirectChatSerializer
    
    def get(self, request, user_id):
        """Get or create a chat with the specified user."""
        current_user = request.user
        
        try:
            other_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Check if they are friends
        user1, user2 = sorted([current_user, other_user], key=lambda u: u.id)
        friendship = Friendship.objects.filter(
            user_one=user1, 
            user_two=user2, 
            status=Friendship.Status.ACCEPTED
        ).first()
        
        if not friendship:
            return Response(
                {'error': 'You can only chat with friends'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get or create direct chat
        chat, created = DirectChat.objects.get_or_create(
            user_one=user1,
            user_two=user2
        )
        
        serializer = DirectChatSerializer(chat)
        return Response(serializer.data)


class DirectMessageListView(generics.ListCreateAPIView):
    """List messages in a chat or send a new message."""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DirectMessageSerializer
    
    def get_queryset(self):
        chat_id = self.kwargs.get('chat_id')
        chat = DirectChat.objects.filter(id=chat_id).first()
        
        if not chat:
            return DirectMessage.objects.none()
        
        # Ensure user is part of the chat
        if self.request.user not in [chat.user_one, chat.user_two]:
            return DirectMessage.objects.none()
        
        return DirectMessage.objects.filter(chat=chat).order_by('created_at')
    
    def create(self, request, *args, **kwargs):
        # DEBUG: Print request data
        print(f"DEBUG: Received POST data: {request.data}")
        
        chat_id = self.kwargs.get('chat_id')
        
        try:
            chat = DirectChat.objects.get(id=chat_id)
        except DirectChat.DoesNotExist:
            return Response({'error': 'Chat not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Ensure user is part of the chat
        if request.user not in [chat.user_one, chat.user_two]:
            return Response({'error': 'You are not part of this chat'}, status=status.HTTP_403_FORBIDDEN)
        
        # Create message
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            print(f"DEBUG: Validation errors: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Save with chat and sender
        message = serializer.save(chat=chat, sender=request.user)
        
        # Update last_message_at
        chat.last_message_at = models.functions.Now()
        chat.save()
        
        print(f"DEBUG: Message saved successfully: {message.id}")
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)
