"""
EVE-NG App Filters - Filtres personnalisés pour l'API
"""
import django_filters
from django_filters import rest_framework as filters
from django.db import models
from django.db.models import Q, Count
from .models import (
    EVENServer, EVENLab, EVENNode, EVENNetwork,
    EVENLink, EVENImage, EVENUserSession
)


# ============================================================================
# FILTRES POUR SERVEURS EVE-NG
# ============================================================================

class EVENServerFilter(filters.FilterSet):
    """Filtres pour EVENServer"""
    name = filters.CharFilter(lookup_expr='icontains')
    description = filters.CharFilter(lookup_expr='icontains')
    url = filters.CharFilter(lookup_expr='icontains')
    status = filters.ChoiceFilter(choices=EVENServer.STATUS_CHOICES)
    
    # Date filters
    created_after = filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    updated_after = filters.DateTimeFilter(field_name='updated_at', lookup_expr='gte')
    updated_before = filters.DateTimeFilter(field_name='updated_at', lookup_expr='lte')
    last_sync_after = filters.DateTimeFilter(field_name='last_sync_at', lookup_expr='gte')
    last_sync_before = filters.DateTimeFilter(field_name='last_sync_at', lookup_expr='lte')
    
    # Relations
    created_by = filters.UUIDFilter(field_name='created_by__id')
    created_by_name = filters.CharFilter(field_name='created_by__email', lookup_expr='icontains')
    
    # Stats filters
    min_labs = filters.NumberFilter(method='filter_min_labs')
    max_labs = filters.NumberFilter(method='filter_max_labs')
    min_images = filters.NumberFilter(method='filter_min_images')
    max_images = filters.NumberFilter(method='filter_max_images')
    
    # Usage filters
    min_cpu = filters.NumberFilter(field_name='cpu_usage', lookup_expr='gte')
    max_cpu = filters.NumberFilter(field_name='cpu_usage', lookup_expr='lte')
    min_memory = filters.NumberFilter(field_name='memory_usage', lookup_expr='gte')
    max_memory = filters.NumberFilter(field_name='memory_usage', lookup_expr='lte')
    
    is_active = filters.BooleanFilter(field_name='status', method='filter_is_active')
    
    class Meta:
        model = EVENServer
        fields = ['name', 'status', 'created_by']
    
    def filter_min_labs(self, queryset, name, value):
        return queryset.annotate(labs_count=Count('labs')).filter(labs_count__gte=value)
    
    def filter_max_labs(self, queryset, name, value):
        return queryset.annotate(labs_count=Count('labs')).filter(labs_count__lte=value)
    
    def filter_min_images(self, queryset, name, value):
        return queryset.annotate(images_count=Count('images')).filter(images_count__gte=value)
    
    def filter_max_images(self, queryset, name, value):
        return queryset.annotate(images_count=Count('images')).filter(images_count__lte=value)
    
    def filter_is_active(self, queryset, name, value):
        if value:
            return queryset.filter(status='active')
        return queryset.exclude(status='active')


# ============================================================================
# FILTRES POUR LABORATOIRES EVE-NG
# ============================================================================

class EVENLabFilter(filters.FilterSet):
    """Filtres pour EVENLab"""
    name = filters.CharFilter(lookup_expr='icontains')
    description = filters.CharFilter(lookup_expr='icontains')
    lab_path = filters.CharFilter(lookup_expr='icontains')
    folder = filters.CharFilter(lookup_expr='icontains')
    status = filters.ChoiceFilter(choices=EVENLab.LAB_STATUS_CHOICES)
    is_active = filters.BooleanFilter()
    
    # Server filters
    server = filters.UUIDFilter(field_name='server__id')
    server_name = filters.CharFilter(field_name='server__name', lookup_expr='icontains')
    
    # Stats filters
    min_nodes = filters.NumberFilter(field_name='node_count', lookup_expr='gte')
    max_nodes = filters.NumberFilter(field_name='node_count', lookup_expr='lte')
    min_links = filters.NumberFilter(field_name='link_count', lookup_expr='gte')
    max_links = filters.NumberFilter(field_name='link_count', lookup_expr='lte')
    
    # Date filters
    created_after = filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    updated_after = filters.DateTimeFilter(field_name='updated_at', lookup_expr='gte')
    updated_before = filters.DateTimeFilter(field_name='updated_at', lookup_expr='lte')
    synced_after = filters.DateTimeFilter(field_name='synced_at', lookup_expr='gte')
    synced_before = filters.DateTimeFilter(field_name='synced_at', lookup_expr='lte')
    
    # Created by
    created_by = filters.UUIDFilter(field_name='created_by__id')
    created_by_name = filters.CharFilter(field_name='created_by__email', lookup_expr='icontains')
    
    class Meta:
        model = EVENLab
        fields = ['name', 'status', 'is_active', 'server', 'created_by']


# ============================================================================
# FILTRES POUR NŒUDS EVE-NG
# ============================================================================

class EVENNodeFilter(filters.FilterSet):
    """Filtres pour EVENNode"""
    name = filters.CharFilter(lookup_expr='icontains')
    node_type = filters.ChoiceFilter(choices=EVENNode.NODE_TYPE_CHOICES)
    status = filters.ChoiceFilter(choices=EVENNode.NODE_STATUS_CHOICES)
    image = filters.CharFilter(lookup_expr='icontains')
    template = filters.CharFilter(lookup_expr='icontains')
    
    # Lab filters
    lab = filters.UUIDFilter(field_name='lab__id')
    lab_name = filters.CharFilter(field_name='lab__name', lookup_expr='icontains')
    server = filters.UUIDFilter(field_name='lab__server__id')
    
    # Hardware filters
    min_cpu = filters.NumberFilter(field_name='cpu', lookup_expr='gte')
    max_cpu = filters.NumberFilter(field_name='cpu', lookup_expr='lte')
    min_ram = filters.NumberFilter(field_name='ram', lookup_expr='gte')
    max_ram = filters.NumberFilter(field_name='ram', lookup_expr='lte')
    min_ethernet = filters.NumberFilter(field_name='ethernet', lookup_expr='gte')
    max_ethernet = filters.NumberFilter(field_name='ethernet', lookup_expr='lte')
    
    # Position filters
    min_x = filters.NumberFilter(field_name='position_x', lookup_expr='gte')
    max_x = filters.NumberFilter(field_name='position_x', lookup_expr='lte')
    min_y = filters.NumberFilter(field_name='position_y', lookup_expr='gte')
    max_y = filters.NumberFilter(field_name='position_y', lookup_expr='lte')
    
    # Console filters
    console_type = filters.ChoiceFilter(choices=EVENNode.CONSOLE_TYPE_CHOICES)
    console_port = filters.NumberFilter()
    min_console_port = filters.NumberFilter(field_name='console_port', lookup_expr='gte')
    max_console_port = filters.NumberFilter(field_name='console_port', lookup_expr='lte')
    
    # Date filters
    created_after = filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    
    class Meta:
        model = EVENNode
        fields = ['name', 'node_type', 'status', 'lab', 'console_type']


# ============================================================================
# FILTRES POUR RÉSEAUX EVE-NG
# ============================================================================

class EVENNetworkFilter(filters.FilterSet):
    """Filtres pour EVENNetwork"""
    name = filters.CharFilter(lookup_expr='icontains')
    network_type = filters.ChoiceFilter(choices=EVENNetwork.NETWORK_TYPE_CHOICES)
    
    # Lab filters
    lab = filters.UUIDFilter(field_name='lab__id')
    lab_name = filters.CharFilter(field_name='lab__name', lookup_expr='icontains')
    server = filters.UUIDFilter(field_name='lab__server__id')
    
    # Network ID
    network_id = filters.NumberFilter()
    min_network_id = filters.NumberFilter(field_name='network_id', lookup_expr='gte')
    max_network_id = filters.NumberFilter(field_name='network_id', lookup_expr='lte')
    
    # Date filters
    created_after = filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    
    class Meta:
        model = EVENNetwork
        fields = ['name', 'network_type', 'lab']


# ============================================================================
# FILTRES POUR LIENS EVE-NG
# ============================================================================

class EVENLinkFilter(filters.FilterSet):
    """Filtres pour EVENLink"""
    link_type = filters.ChoiceFilter(choices=EVENLink.LINK_TYPE_CHOICES)
    
    # Lab filters
    lab = filters.UUIDFilter(field_name='lab__id')
    lab_name = filters.CharFilter(field_name='lab__name', lookup_expr='icontains')
    server = filters.UUIDFilter(field_name='lab__server__id')
    
    # Node filters
    source_node = filters.UUIDFilter(field_name='source_node__id')
    source_node_name = filters.CharFilter(field_name='source_node__name', lookup_expr='icontains')
    destination_node = filters.UUIDFilter(field_name='destination_node__id')
    destination_node_name = filters.CharFilter(field_name='destination_node__name', lookup_expr='icontains')
    
    # Date filters
    created_after = filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    
    class Meta:
        model = EVENLink
        fields = ['link_type', 'lab', 'source_node', 'destination_node']


# ============================================================================
# FILTRES POUR IMAGES EVE-NG
# ============================================================================

class EVENImageFilter(filters.FilterSet):
    """Filtres pour EVENImage"""
    name = filters.CharFilter(lookup_expr='icontains')
    image_type = filters.ChoiceFilter(choices=EVENImage.IMAGE_TYPE_CHOICES)
    version = filters.CharFilter(lookup_expr='icontains')
    
    # Server filters
    server = filters.UUIDFilter(field_name='server__id')
    server_name = filters.CharFilter(field_name='server__name', lookup_expr='icontains')
    
    # Size filters
    min_size = filters.NumberFilter(field_name='size_mb', lookup_expr='gte')
    max_size = filters.NumberFilter(field_name='size_mb', lookup_expr='lte')
    
    # Hardware defaults
    min_default_cpu = filters.NumberFilter(field_name='default_cpu', lookup_expr='gte')
    max_default_cpu = filters.NumberFilter(field_name='default_cpu', lookup_expr='lte')
    min_default_ram = filters.NumberFilter(field_name='default_ram', lookup_expr='gte')
    max_default_ram = filters.NumberFilter(field_name='default_ram', lookup_expr='lte')
    
    # Date filters
    created_after = filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    synced_after = filters.DateTimeFilter(field_name='synced_at', lookup_expr='gte')
    synced_before = filters.DateTimeFilter(field_name='synced_at', lookup_expr='lte')
    
    class Meta:
        model = EVENImage
        fields = ['name', 'image_type', 'server']


# ============================================================================
# FILTRES POUR SESSIONS UTILISATEURS
# ============================================================================

class EVENUserSessionFilter(filters.FilterSet):
    """Filtres pour EVENUserSession"""
    is_active = filters.BooleanFilter()
    
    # Server filters
    server = filters.UUIDFilter(field_name='server__id')
    server_name = filters.CharFilter(field_name='server__name', lookup_expr='icontains')
    
    # User filters
    user = filters.UUIDFilter(field_name='user__id')
    user_email = filters.CharFilter(field_name='user__email', lookup_expr='icontains')
    
    # Date filters
    logged_in_after = filters.DateTimeFilter(field_name='logged_in_at', lookup_expr='gte')
    logged_in_before = filters.DateTimeFilter(field_name='logged_in_at', lookup_expr='lte')
    last_activity_after = filters.DateTimeFilter(field_name='last_activity_at', lookup_expr='gte')
    last_activity_before = filters.DateTimeFilter(field_name='last_activity_at', lookup_expr='lte')
    expires_after = filters.DateTimeFilter(field_name='expires_at', lookup_expr='gte')
    expires_before = filters.DateTimeFilter(field_name='expires_at', lookup_expr='lte')
    
    class Meta:
        model = EVENUserSession
        fields = ['is_active', 'server', 'user']