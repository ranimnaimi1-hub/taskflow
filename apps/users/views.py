"""
Users Views with custom responses
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters

from .models import User, Team, Role, Permission, UserActivity
from .serializers import (
    UserListSerializer, UserDetailSerializer, UserCreateSerializer,
    TeamSerializer, RoleSerializer, PermissionSerializer,
    UserActivitySerializer, ChangePasswordSerializer
)
from apps.core.permissions import IsAdmin, IsAdminOrReadOnly
from apps.core.responses import success_response, created_response, error_response
from apps.core.pagination import StandardPagination


class UserViewSet(viewsets.ModelViewSet):
    """User ViewSet with custom responses"""
    queryset = User.objects.all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['role', 'status', 'department', 'is_active']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    ordering_fields = ['created_at', 'last_login', 'username']
    ordering = ['-created_at']
    pagination_class = StandardPagination
    
    def get_serializer_class(self):
        if self.action == 'list':
            return UserListSerializer
        elif self.action == 'create':
            return UserCreateSerializer
        return UserDetailSerializer
    
    def get_permissions(self):
        if self.action == 'create':
            return [AllowAny()]
        elif self.action in ['update', 'partial_update', 'destroy']:
            return [IsAdmin()]
        return [IsAuthenticated()]
    
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return success_response(serializer.data, "Users retrieved successfully")
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return created_response(
            UserDetailSerializer(user).data,
            "User created successfully"
        )
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """Get current user"""
        serializer = UserDetailSerializer(request.user)
        return success_response(serializer.data, "Current user retrieved")
    
    @action(detail=False, methods=['post'])
    def change_password(self, request):
        """Change password"""
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        
        return success_response(None, "Password changed successfully")
    
    @action(detail=True, methods=['get'])
    def activities(self, request, pk=None):
        """Get user activities"""
        user = self.get_object()
        activities = user.activities.all()
        
        page = self.paginate_queryset(activities)
        if page is not None:
            serializer = UserActivitySerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = UserActivitySerializer(activities, many=True)
        return success_response(serializer.data, "Activities retrieved")


class TeamViewSet(viewsets.ModelViewSet):
    """Team ViewSet"""
    queryset = Team.objects.all()
    serializer_class = TeamSerializer
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]
    pagination_class = StandardPagination


class RoleViewSet(viewsets.ModelViewSet):
    """Role ViewSet"""
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [IsAuthenticated, IsAdmin]


class PermissionViewSet(viewsets.ReadOnlyModelViewSet):
    """Permission ViewSet - Read only"""
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer
    permission_classes = [IsAuthenticated]


class UserActivityViewSet(viewsets.ReadOnlyModelViewSet):
    """User Activity ViewSet - Read only"""
    queryset = UserActivity.objects.all()
    serializer_class = UserActivitySerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['user', 'action', 'severity']
    ordering = ['-created_at']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        # Non-admins see only their own activities
        if not user.is_admin:
            queryset = queryset.filter(user=user)
        
        return queryset
