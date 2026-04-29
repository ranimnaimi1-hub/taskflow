"""
Monitoring App Filters - Filtres personnalisés pour l'API
"""
import django_filters
from django_filters import rest_framework as filters
from django.db import models
from django.db.models import Q, Count, Avg, Min, Max
from .models import (
    SystemMetric, DeviceMetric, InterfaceMetric, ApplicationMetric,
    Alert, AlertThreshold, NotificationChannel, NotificationLog,
    Dashboard, MetricCollection
)


# ============================================================================
# FILTRES POUR MÉTRIQUES SYSTÈME
# ============================================================================

class SystemMetricFilter(filters.FilterSet):
    """Filtres pour SystemMetric"""
    
    # Plages de valeurs
    min_cpu = filters.NumberFilter(field_name='cpu_usage', lookup_expr='gte')
    max_cpu = filters.NumberFilter(field_name='cpu_usage', lookup_expr='lte')
    min_memory = filters.NumberFilter(field_name='memory_percent', lookup_expr='gte')
    max_memory = filters.NumberFilter(field_name='memory_percent', lookup_expr='lte')
    min_disk = filters.NumberFilter(field_name='disk_percent', lookup_expr='gte')
    max_disk = filters.NumberFilter(field_name='disk_percent', lookup_expr='lte')
    
    # Dates
    collected_after = filters.DateTimeFilter(field_name='collected_at', lookup_expr='gte')
    collected_before = filters.DateTimeFilter(field_name='collected_at', lookup_expr='lte')
    created_after = filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    
    class Meta:
        model = SystemMetric
        fields = ['collected_at']


# ============================================================================
# FILTRES POUR MÉTRIQUES DES ÉQUIPEMENTS
# ============================================================================

class DeviceMetricFilter(filters.FilterSet):
    """Filtres pour DeviceMetric"""
    
    # Device filters
    device = filters.UUIDFilter(field_name='device__id')
    device_name = filters.CharFilter(field_name='device__name', lookup_expr='icontains')
    device_hostname = filters.CharFilter(field_name='device__hostname', lookup_expr='icontains')
    site = filters.UUIDFilter(field_name='device__site__id')
    site_name = filters.CharFilter(field_name='device__site__name', lookup_expr='icontains')
    
    # Plages de valeurs
    min_cpu = filters.NumberFilter(field_name='cpu_usage', lookup_expr='gte')
    max_cpu = filters.NumberFilter(field_name='cpu_usage', lookup_expr='lte')
    min_memory = filters.NumberFilter(field_name='memory_usage', lookup_expr='gte')
    max_memory = filters.NumberFilter(field_name='memory_usage', lookup_expr='lte')
    min_temperature = filters.NumberFilter(field_name='temperature', lookup_expr='gte')
    max_temperature = filters.NumberFilter(field_name='temperature', lookup_expr='lte')
    min_response_time = filters.NumberFilter(field_name='response_time', lookup_expr='gte')
    max_response_time = filters.NumberFilter(field_name='response_time', lookup_expr='lte')
    
    # Statut
    is_reachable = filters.BooleanFilter(field_name='is_reachable')
    
    # Dates
    collected_after = filters.DateTimeFilter(field_name='collected_at', lookup_expr='gte')
    collected_before = filters.DateTimeFilter(field_name='collected_at', lookup_expr='lte')
    
    class Meta:
        model = DeviceMetric
        fields = ['device', 'is_reachable', 'collected_at']


# ============================================================================
# FILTRES POUR MÉTRIQUES DES INTERFACES
# ============================================================================

class InterfaceMetricFilter(filters.FilterSet):
    """Filtres pour InterfaceMetric"""
    
    # Interface filters
    interface = filters.UUIDFilter(field_name='interface__id')
    interface_name = filters.CharFilter(field_name='interface__name', lookup_expr='icontains')
    device = filters.UUIDFilter(field_name='interface__device__id')
    device_name = filters.CharFilter(field_name='interface__device__name', lookup_expr='icontains')
    
    # Statut
    status = filters.CharFilter(field_name='status', lookup_expr='icontains')
    
    # Plages de valeurs
    min_rx_bytes = filters.NumberFilter(field_name='rx_bytes', lookup_expr='gte')
    max_rx_bytes = filters.NumberFilter(field_name='rx_bytes', lookup_expr='lte')
    min_tx_bytes = filters.NumberFilter(field_name='tx_bytes', lookup_expr='gte')
    max_tx_bytes = filters.NumberFilter(field_name='tx_bytes', lookup_expr='lte')
    min_rx_errors = filters.NumberFilter(field_name='rx_errors', lookup_expr='gte')
    max_rx_errors = filters.NumberFilter(field_name='rx_errors', lookup_expr='lte')
    min_tx_errors = filters.NumberFilter(field_name='tx_errors', lookup_expr='gte')
    max_tx_errors = filters.NumberFilter(field_name='tx_errors', lookup_expr='lte')
    min_rx_rate = filters.NumberFilter(field_name='rx_rate_bps', lookup_expr='gte')
    max_rx_rate = filters.NumberFilter(field_name='rx_rate_bps', lookup_expr='lte')
    min_tx_rate = filters.NumberFilter(field_name='tx_rate_bps', lookup_expr='gte')
    max_tx_rate = filters.NumberFilter(field_name='tx_rate_bps', lookup_expr='lte')
    
    # Dates
    collected_after = filters.DateTimeFilter(field_name='collected_at', lookup_expr='gte')
    collected_before = filters.DateTimeFilter(field_name='collected_at', lookup_expr='lte')
    
    class Meta:
        model = InterfaceMetric
        fields = ['interface', 'device', 'status', 'collected_at']


# ============================================================================
# FILTRES POUR MÉTRIQUES APPLICATIVES
# ============================================================================

class ApplicationMetricFilter(filters.FilterSet):
    """Filtres pour ApplicationMetric"""
    
    metric_type = filters.ChoiceFilter(choices=ApplicationMetric.METRIC_TYPE_CHOICES)
    metric_name = filters.CharFilter(lookup_expr='icontains')
    
    # Plages de valeurs
    min_value = filters.NumberFilter(field_name='metric_value', lookup_expr='gte')
    max_value = filters.NumberFilter(field_name='metric_value', lookup_expr='lte')
    
    # Tags
    tag_key = filters.CharFilter(method='filter_tag_key')
    tag_value = filters.CharFilter(method='filter_tag_value')
    
    # Dates
    collected_after = filters.DateTimeFilter(field_name='collected_at', lookup_expr='gte')
    collected_before = filters.DateTimeFilter(field_name='collected_at', lookup_expr='lte')
    
    class Meta:
        model = ApplicationMetric
        fields = ['metric_type', 'metric_name']
    
    def filter_tag_key(self, queryset, name, value):
        """Filtre les métriques qui ont une clé de tag spécifique"""
        return queryset.filter(tags__has_key=value)
    
    def filter_tag_value(self, queryset, name, value):
        """Filtre les métriques qui ont une valeur de tag spécifique"""
        result_ids = []
        for metric in queryset:
            if value in metric.tags.values():
                result_ids.append(metric.id)
        return queryset.filter(id__in=result_ids)


# ============================================================================
# FILTRES POUR ALERTES
# ============================================================================

class AlertFilter(filters.FilterSet):
    """Filtres pour Alert"""
    
    name = filters.CharFilter(lookup_expr='icontains')
    description = filters.CharFilter(lookup_expr='icontains')
    severity = filters.ChoiceFilter(choices=Alert.SEVERITY_CHOICES)
    status = filters.ChoiceFilter(choices=Alert.STATUS_CHOICES)
    source = filters.ChoiceFilter(choices=Alert.SOURCE_CHOICES)
    
    # Device filters
    device = filters.UUIDFilter(field_name='device__id')
    device_name = filters.CharFilter(field_name='device__name', lookup_expr='icontains')
    device_hostname = filters.CharFilter(field_name='device__hostname', lookup_expr='icontains')
    
    # Interface filters
    interface = filters.UUIDFilter(field_name='interface__id')
    interface_name = filters.CharFilter(field_name='interface__name', lookup_expr='icontains')
    
    # Dates
    first_occurrence_after = filters.DateTimeFilter(field_name='first_occurrence', lookup_expr='gte')
    first_occurrence_before = filters.DateTimeFilter(field_name='first_occurrence', lookup_expr='lte')
    last_occurrence_after = filters.DateTimeFilter(field_name='last_occurrence', lookup_expr='gte')
    last_occurrence_before = filters.DateTimeFilter(field_name='last_occurrence', lookup_expr='lte')
    acknowledged_after = filters.DateTimeFilter(field_name='acknowledged_at', lookup_expr='gte')
    acknowledged_before = filters.DateTimeFilter(field_name='acknowledged_at', lookup_expr='lte')
    resolved_after = filters.DateTimeFilter(field_name='resolved_at', lookup_expr='gte')
    resolved_before = filters.DateTimeFilter(field_name='resolved_at', lookup_expr='lte')
    
    # Count filters
    min_occurrences = filters.NumberFilter(field_name='occurrence_count', lookup_expr='gte')
    max_occurrences = filters.NumberFilter(field_name='occurrence_count', lookup_expr='lte')
    
    # Acknowledged by
    acknowledged_by = filters.UUIDFilter(field_name='acknowledged_by__id')
    acknowledged_by_name = filters.CharFilter(field_name='acknowledged_by__email', lookup_expr='icontains')
    
    class Meta:
        model = Alert
        fields = ['name', 'severity', 'status', 'source', 'device', 'interface']


# ============================================================================
# FILTRES POUR SEUILS D'ALERTE
# ============================================================================

class AlertThresholdFilter(filters.FilterSet):
    """Filtres pour AlertThreshold"""
    
    name = filters.CharFilter(lookup_expr='icontains')
    threshold_type = filters.ChoiceFilter(choices=AlertThreshold.THRESHOLD_TYPE_CHOICES)
    is_enabled = filters.BooleanFilter()
    
    # Device filters
    device = filters.UUIDFilter(method='filter_device')
    device_name = filters.CharFilter(method='filter_device_name')
    
    # Plages de valeurs
    min_warning = filters.NumberFilter(field_name='warning_threshold', lookup_expr='gte')
    max_warning = filters.NumberFilter(field_name='warning_threshold', lookup_expr='lte')
    min_critical = filters.NumberFilter(field_name='critical_threshold', lookup_expr='gte')
    max_critical = filters.NumberFilter(field_name='critical_threshold', lookup_expr='lte')
    
    # Created by
    created_by = filters.UUIDFilter(field_name='created_by__id')
    created_by_name = filters.CharFilter(field_name='created_by__email', lookup_expr='icontains')
    
    class Meta:
        model = AlertThreshold
        fields = ['name', 'threshold_type', 'is_enabled', 'created_by']
    
    def filter_device(self, queryset, name, value):
        """Filtre les seuils appliqués à un appareil spécifique"""
        return queryset.filter(devices__id=value)
    
    def filter_device_name(self, queryset, name, value):
        """Filtre les seuils appliqués à un appareil (par nom)"""
        return queryset.filter(devices__name__icontains=value).distinct()


# ============================================================================
# FILTRES POUR CANAUX DE NOTIFICATION
# ============================================================================

class NotificationChannelFilter(filters.FilterSet):
    """Filtres pour NotificationChannel"""
    
    name = filters.CharFilter(lookup_expr='icontains')
    channel_type = filters.ChoiceFilter(choices=NotificationChannel.CHANNEL_TYPE_CHOICES)
    is_enabled = filters.BooleanFilter()
    
    class Meta:
        model = NotificationChannel
        fields = ['name', 'channel_type', 'is_enabled']


# ============================================================================
# FILTRES POUR LOGS DE NOTIFICATION
# ============================================================================

class NotificationLogFilter(filters.FilterSet):
    """Filtres pour NotificationLog"""
    
    alert = filters.UUIDFilter(field_name='alert__id')
    alert_name = filters.CharFilter(field_name='alert__name', lookup_expr='icontains')
    channel = filters.UUIDFilter(field_name='channel__id')
    channel_name = filters.CharFilter(field_name='channel__name', lookup_expr='icontains')
    status = filters.ChoiceFilter(choices=[('sent', 'Sent'), ('failed', 'Failed'), ('pending', 'Pending')])
    
    # Dates
    sent_after = filters.DateTimeFilter(field_name='sent_at', lookup_expr='gte')
    sent_before = filters.DateTimeFilter(field_name='sent_at', lookup_expr='lte')
    
    class Meta:
        model = NotificationLog
        fields = ['alert', 'channel', 'status']


# ============================================================================
# FILTRES POUR TABLEAUX DE BORD
# ============================================================================

class DashboardFilter(filters.FilterSet):
    """Filtres pour Dashboard"""
    
    name = filters.CharFilter(lookup_expr='icontains')
    description = filters.CharFilter(lookup_expr='icontains')
    is_public = filters.BooleanFilter()
    
    # Owner filters
    owner = filters.UUIDFilter(field_name='owner__id')
    owner_name = filters.CharFilter(field_name='owner__email', lookup_expr='icontains')
    
    class Meta:
        model = Dashboard
        fields = ['name', 'is_public', 'owner']


# ============================================================================
# FILTRES POUR COLLECTIONS DE MÉTRIQUES
# ============================================================================

class MetricCollectionFilter(filters.FilterSet):
    """Filtres pour MetricCollection"""
    
    name = filters.CharFilter(lookup_expr='icontains')
    metric_type = filters.ChoiceFilter(choices=ApplicationMetric.METRIC_TYPE_CHOICES)
    aggregation = filters.ChoiceFilter(choices=[('avg', 'Average'), ('min', 'Minimum'),
                                                ('max', 'Maximum'), ('sum', 'Sum')])
    
    class Meta:
        model = MetricCollection
        fields = ['name', 'metric_type', 'aggregation']