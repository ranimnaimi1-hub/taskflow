"""
Monitoring App Serializers - API serializers professionnels
"""
from rest_framework import serializers
from django.utils import timezone
from .models import (
    SystemMetric, DeviceMetric, InterfaceMetric, ApplicationMetric,
    Alert, AlertThreshold, NotificationChannel, NotificationLog,
    Dashboard, MetricCollection
)
from apps.inventory.models import Device, Interface
from apps.users.models import User


# ============================================================================
# MÉTRIQUES SYSTÈME
# ============================================================================

class SystemMetricSerializer(serializers.ModelSerializer):
    """Serializer pour les métriques système"""
    collected_at_formatted = serializers.DateTimeField(source='collected_at', read_only=True)
    
    class Meta:
        model = SystemMetric
        fields = [
            'id', 'cpu_usage', 'cpu_count', 'load_avg_1min', 'load_avg_5min', 'load_avg_15min',
            'memory_total', 'memory_available', 'memory_used', 'memory_percent',
            'disk_total', 'disk_used', 'disk_free', 'disk_percent',
            'network_bytes_sent', 'network_bytes_recv', 'network_packets_sent', 'network_packets_recv',
            'collected_at', 'collected_at_formatted', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class SystemMetricDetailSerializer(SystemMetricSerializer):
    """Serializer détaillé pour les métriques système"""
    
    class Meta(SystemMetricSerializer.Meta):
        fields = SystemMetricSerializer.Meta.fields


# ============================================================================
# MÉTRIQUES DES ÉQUIPEMENTS
# ============================================================================

class DeviceMetricSerializer(serializers.ModelSerializer):
    """Serializer pour les métriques des équipements"""
    device_name = serializers.CharField(source='device.name', read_only=True)
    device_hostname = serializers.CharField(source='device.hostname', read_only=True)
    device_ip = serializers.CharField(source='device.management_ip', read_only=True)
    collected_at_formatted = serializers.DateTimeField(source='collected_at', read_only=True)
    
    class Meta:
        model = DeviceMetric
        fields = [
            'id', 'device', 'device_name', 'device_hostname', 'device_ip',
            'cpu_usage', 'memory_usage', 'temperature', 'uptime',
            'is_reachable', 'response_time',
            'collected_at', 'collected_at_formatted', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class DeviceMetricDetailSerializer(DeviceMetricSerializer):
    """Serializer détaillé pour les métriques des équipements"""
    
    class Meta(DeviceMetricSerializer.Meta):
        fields = DeviceMetricSerializer.Meta.fields


# ============================================================================
# MÉTRIQUES DES INTERFACES
# ============================================================================

class InterfaceMetricSerializer(serializers.ModelSerializer):
    """Serializer pour les métriques des interfaces"""
    device_name = serializers.CharField(source='interface.device.name', read_only=True)
    device_hostname = serializers.CharField(source='interface.device.hostname', read_only=True)
    interface_name = serializers.CharField(source='interface.name', read_only=True)
    collected_at_formatted = serializers.DateTimeField(source='collected_at', read_only=True)
    
    class Meta:
        model = InterfaceMetric
        fields = [
            'id', 'interface', 'device_name', 'device_hostname', 'interface_name',
            'status', 'rx_bytes', 'tx_bytes', 'rx_packets', 'tx_packets',
            'rx_errors', 'tx_errors', 'rx_drops', 'tx_drops',
            'rx_rate_bps', 'tx_rate_bps',
            'collected_at', 'collected_at_formatted', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class InterfaceMetricDetailSerializer(InterfaceMetricSerializer):
    """Serializer détaillé pour les métriques des interfaces"""
    
    class Meta(InterfaceMetricSerializer.Meta):
        fields = InterfaceMetricSerializer.Meta.fields


# ============================================================================
# MÉTRIQUES APPLICATIVES
# ============================================================================

class ApplicationMetricSerializer(serializers.ModelSerializer):
    """Serializer pour les métriques applicatives"""
    metric_type_display = serializers.CharField(source='get_metric_type_display', read_only=True)
    collected_at_formatted = serializers.DateTimeField(source='collected_at', read_only=True)
    
    class Meta:
        model = ApplicationMetric
        fields = [
            'id', 'metric_type', 'metric_type_display', 'metric_name', 'metric_value',
            'tags', 'collected_at', 'collected_at_formatted', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class ApplicationMetricDetailSerializer(ApplicationMetricSerializer):
    """Serializer détaillé pour les métriques applicatives"""
    
    class Meta(ApplicationMetricSerializer.Meta):
        fields = ApplicationMetricSerializer.Meta.fields


# ============================================================================
# ALERTES
# ============================================================================

class AlertSerializer(serializers.ModelSerializer):
    """Serializer pour les alertes"""
    severity_display = serializers.CharField(source='get_severity_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    source_display = serializers.CharField(source='get_source_display', read_only=True)
    device_name = serializers.CharField(source='device.name', read_only=True, allow_null=True)
    device_hostname = serializers.CharField(source='device.hostname', read_only=True, allow_null=True)
    interface_name = serializers.CharField(source='interface.name', read_only=True, allow_null=True)
    acknowledged_by_name = serializers.CharField(source='acknowledged_by.get_full_name', read_only=True, allow_null=True)
    
    class Meta:
        model = Alert
        fields = [
            'id', 'name', 'description', 'severity', 'severity_display',
            'status', 'status_display', 'source', 'source_display',
            'device', 'device_name', 'device_hostname',
            'interface', 'interface_name',
            'metric_name', 'metric_value', 'threshold_value', 'operator',
            'first_occurrence', 'last_occurrence', 'occurrence_count',
            'acknowledged_by', 'acknowledged_by_name', 'acknowledged_at',
            'resolved_at', 'notifications_sent', 'last_notification_at',
            'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'first_occurrence',
            'last_occurrence', 'occurrence_count', 'notifications_sent'
        ]


class AlertDetailSerializer(AlertSerializer):
    """Serializer détaillé pour les alertes"""
    notifications = serializers.SerializerMethodField()
    
    class Meta(AlertSerializer.Meta):
        fields = AlertSerializer.Meta.fields + ['notifications']
    
    def get_notifications(self, obj):
        notifications = obj.notifications.all()[:5]
        return [{
            'id': str(n.id),
            'channel_name': n.channel.name,
            'status': n.status,
            'sent_at': n.sent_at
        } for n in notifications]


# ============================================================================
# SEUILS D'ALERTE
# ============================================================================

class AlertThresholdSerializer(serializers.ModelSerializer):
    """Serializer pour les seuils d'alerte"""
    threshold_type_display = serializers.CharField(source='get_threshold_type_display', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True, allow_null=True)
    
    class Meta:
        model = AlertThreshold
        fields = [
            'id', 'name', 'threshold_type', 'threshold_type_display', 'description',
            'warning_threshold', 'critical_threshold', 'operator',
            'duration', 'silence_period', 'devices', 'is_enabled',
            'created_by', 'created_by_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by']


class AlertThresholdDetailSerializer(AlertThresholdSerializer):
    """Serializer détaillé pour les seuils d'alerte"""
    devices_list = serializers.SerializerMethodField()
    
    class Meta(AlertThresholdSerializer.Meta):
        fields = AlertThresholdSerializer.Meta.fields + ['devices_list']
    
    def get_devices_list(self, obj):
        return [{'id': str(d.id), 'name': d.name, 'hostname': d.hostname} 
                for d in obj.devices.all()[:10]]


# ============================================================================
# CANAUX DE NOTIFICATION
# ============================================================================

class NotificationChannelSerializer(serializers.ModelSerializer):
    """Serializer pour les canaux de notification"""
    channel_type_display = serializers.CharField(source='get_channel_type_display', read_only=True)
    
    class Meta:
        model = NotificationChannel
        fields = [
            'id', 'name', 'channel_type', 'channel_type_display', 'description',
            'config', 'is_enabled', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
        extra_kwargs = {
            'config': {'write_only': True},
        }


# ============================================================================
# LOGS DE NOTIFICATION
# ============================================================================

class NotificationLogSerializer(serializers.ModelSerializer):
    """Serializer pour les logs de notification"""
    alert_name = serializers.CharField(source='alert.name', read_only=True)
    channel_name = serializers.CharField(source='channel.name', read_only=True)
    channel_type = serializers.CharField(source='channel.channel_type', read_only=True)
    
    class Meta:
        model = NotificationLog
        fields = [
            'id', 'alert', 'alert_name', 'channel', 'channel_name', 'channel_type',
            'status', 'error_message', 'sent_at', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'sent_at']


# ============================================================================
# TABLEAUX DE BORD
# ============================================================================

class DashboardSerializer(serializers.ModelSerializer):
    """Serializer pour les tableaux de bord"""
    owner_name = serializers.CharField(source='owner.get_full_name', read_only=True, allow_null=True)
    
    class Meta:
        model = Dashboard
        fields = [
            'id', 'name', 'description', 'config', 'widgets',
            'owner', 'owner_name', 'is_public', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class DashboardDetailSerializer(DashboardSerializer):
    """Serializer détaillé pour les tableaux de bord"""
    
    class Meta(DashboardSerializer.Meta):
        fields = DashboardSerializer.Meta.fields


# ============================================================================
# COLLECTIONS DE MÉTRIQUES
# ============================================================================

class MetricCollectionSerializer(serializers.ModelSerializer):
    """Serializer pour les collections de métriques"""
    metric_type_display = serializers.CharField(source='get_metric_type_display', read_only=True)
    
    class Meta:
        model = MetricCollection
        fields = [
            'id', 'name', 'description', 'metric_type', 'metric_type_display',
            'metric_names', 'retention_days', 'aggregation', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


# ============================================================================
# REQUÊTES
# ============================================================================

class MetricQuerySerializer(serializers.Serializer):
    """Serializer pour les requêtes de métriques"""
    metric_type = serializers.ChoiceField(choices=ApplicationMetric.METRIC_TYPE_CHOICES, required=False)
    device_id = serializers.UUIDField(required=False, allow_null=True)
    interface_id = serializers.UUIDField(required=False, allow_null=True)
    metric_name = serializers.CharField(required=False, allow_blank=True)
    start_time = serializers.DateTimeField(required=False)
    end_time = serializers.DateTimeField(required=False)
    interval = serializers.CharField(required=False, default='1h',
                                     help_text="Aggregation interval (e.g., 1m, 5m, 1h, 1d)")
    aggregation = serializers.ChoiceField(required=False, default='avg',
                                          choices=[('avg', 'Average'), ('min', 'Minimum'),
                                                   ('max', 'Maximum'), ('sum', 'Sum')])


class AlertAcknowledgeSerializer(serializers.Serializer):
    """Serializer pour acquitter une alerte"""
    notes = serializers.CharField(required=False, allow_blank=True)


# ============================================================================
# DASHBOARD
# ============================================================================

class MonitoringStatsSerializer(serializers.Serializer):
    """Serializer pour les statistiques du dashboard"""
    system = serializers.DictField()
    devices = serializers.DictField()
    applications = serializers.DictField()
    alerts = serializers.DictField()


class RecentAlertSerializer(serializers.Serializer):
    """Serializer pour les alertes récentes"""
    id = serializers.UUIDField()
    name = serializers.CharField()
    severity = serializers.CharField()
    status = serializers.CharField()
    device_name = serializers.CharField(allow_null=True)
    last_occurrence = serializers.DateTimeField()


class TopDeviceMetricSerializer(serializers.Serializer):
    """Serializer pour les métriques des équipements"""
    device_id = serializers.UUIDField()
    device_name = serializers.CharField()
    cpu_usage = serializers.FloatField(allow_null=True)
    memory_usage = serializers.FloatField(allow_null=True)
    is_reachable = serializers.BooleanField()


class MonitoringDashboardSerializer(serializers.Serializer):
    """Serializer pour le dashboard monitoring"""
    statistics = MonitoringStatsSerializer()
    recent_alerts = RecentAlertSerializer(many=True)
    top_devices = TopDeviceMetricSerializer(many=True)
    system_metrics = SystemMetricSerializer(many=True)
    application_metrics = serializers.ListField(child=serializers.DictField())