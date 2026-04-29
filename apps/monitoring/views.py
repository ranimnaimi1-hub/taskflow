"""
Monitoring App Views - API endpoints professionnels
"""
from rest_framework import viewsets, status
from rest_framework import filters as drf_filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count, Q, Avg, Min, Max
from django.utils import timezone
from datetime import timedelta
import logging

from apps.core.permissions import IsActiveUser, HasAPIAccess, IsAdmin
from apps.core.pagination import StandardPagination
from apps.core.responses import success_response, created_response, error_response

from .models import (
    SystemMetric, DeviceMetric, InterfaceMetric, ApplicationMetric,
    Alert, AlertThreshold, NotificationChannel, NotificationLog,
    Dashboard, MetricCollection
)
from .serializers import (
    SystemMetricSerializer, SystemMetricDetailSerializer,
    DeviceMetricSerializer, DeviceMetricDetailSerializer,
    InterfaceMetricSerializer, InterfaceMetricDetailSerializer,
    ApplicationMetricSerializer, ApplicationMetricDetailSerializer,
    AlertSerializer, AlertDetailSerializer,
    AlertThresholdSerializer, AlertThresholdDetailSerializer,
    NotificationChannelSerializer,
    NotificationLogSerializer,
    DashboardSerializer, DashboardDetailSerializer,
    MetricCollectionSerializer,
    MetricQuerySerializer, AlertAcknowledgeSerializer
)
from .filters import (
    SystemMetricFilter,
    DeviceMetricFilter,
    InterfaceMetricFilter,
    ApplicationMetricFilter,
    AlertFilter,
    AlertThresholdFilter,
    NotificationChannelFilter,
    NotificationLogFilter,
    DashboardFilter,
    MetricCollectionFilter
)
from .collectors import SystemCollector, DeviceCollector, ApplicationCollector

logger = logging.getLogger(__name__)


# ============================================================================
# MÉTRIQUES SYSTÈME
# ============================================================================

class SystemMetricViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet pour les métriques système (lecture seule)"""
    
    queryset = SystemMetric.objects.all()
    serializer_class = SystemMetricSerializer
    serializer_classes = {
        'retrieve': SystemMetricDetailSerializer,
        'default': SystemMetricSerializer
    }
    
    permission_classes = [IsAuthenticated, IsActiveUser, HasAPIAccess]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_class = SystemMetricFilter
    ordering_fields = ['collected_at', 'cpu_usage', 'memory_percent', 'disk_percent']
    ordering = ['-collected_at']
    
    def get_serializer_class(self):
        return self.serializer_classes.get(self.action, self.serializer_classes['default'])
    
    def get_queryset(self):
        user = self.request.user
        
        if not user or not user.is_authenticated:
            return SystemMetric.objects.none()
        
        if hasattr(user, 'role') and user.role in ['superadmin', 'admin']:
            return SystemMetric.objects.all()
        
        return SystemMetric.objects.all()  # Tout le monde peut voir les métriques système
    
    @action(detail=False, methods=['get'])
    def latest(self, request):
        """Récupère les dernières métriques système"""
        metric = SystemMetric.objects.order_by('-collected_at').first()
        
        if metric:
            serializer = self.get_serializer(metric)
            return success_response(serializer.data, "Latest metrics retrieved")
        
        return error_response("No metrics available")
    
    @action(detail=False, methods=['post'])
    def collect(self, request):
        """Collecte manuelle des métriques système"""
        if not hasattr(request.user, 'role') or request.user.role not in ['superadmin', 'admin']:
            self.permission_denied(request)
        
        # Collecter les métriques
        metrics = SystemCollector.collect_all()
        
        # Créer l'enregistrement
        system_metric = SystemMetric.objects.create(
            cpu_usage=metrics['cpu']['usage_percent'],
            cpu_count=metrics['cpu']['count'],
            load_avg_1min=metrics['cpu']['load_avg'][0] if metrics['cpu']['load_avg'] else None,
            load_avg_5min=metrics['cpu']['load_avg'][1] if metrics['cpu']['load_avg'] else None,
            load_avg_15min=metrics['cpu']['load_avg'][2] if metrics['cpu']['load_avg'] else None,
            memory_total=metrics['memory']['total'],
            memory_available=metrics['memory']['available'],
            memory_used=metrics['memory']['used'],
            memory_percent=metrics['memory']['percent'],
            disk_total=metrics['disk']['total'],
            disk_used=metrics['disk']['used'],
            disk_free=metrics['disk']['free'],
            disk_percent=metrics['disk']['percent'],
            network_bytes_sent=metrics['network']['bytes_sent'],
            network_bytes_recv=metrics['network']['bytes_recv'],
            network_packets_sent=metrics['network']['packets_sent'],
            network_packets_recv=metrics['network']['packets_recv'],
            collected_at=metrics['timestamp']
        )
        
        return created_response(
            SystemMetricDetailSerializer(system_metric).data,
            "Metrics collected successfully"
        )
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Statistiques sur les métriques système"""
        # Dernières 24h
        last_24h = timezone.now() - timedelta(hours=24)
        recent_metrics = SystemMetric.objects.filter(collected_at__gte=last_24h)
        
        stats = {
            'avg_cpu': recent_metrics.aggregate(avg=Avg('cpu_usage'))['avg'],
            'max_cpu': recent_metrics.aggregate(max=Max('cpu_usage'))['max'],
            'avg_memory': recent_metrics.aggregate(avg=Avg('memory_percent'))['avg'],
            'max_memory': recent_metrics.aggregate(max=Max('memory_percent'))['max'],
            'avg_disk': recent_metrics.aggregate(avg=Avg('disk_percent'))['avg'],
            'max_disk': recent_metrics.aggregate(max=Max('disk_percent'))['max'],
            'total_metrics': recent_metrics.count(),
        }
        
        return success_response(stats, "System stats retrieved")


# ============================================================================
# MÉTRIQUES DES ÉQUIPEMENTS
# ============================================================================

class DeviceMetricViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet pour les métriques des équipements (lecture seule)"""
    
    queryset = DeviceMetric.objects.select_related('device').all()
    serializer_class = DeviceMetricSerializer
    serializer_classes = {
        'retrieve': DeviceMetricDetailSerializer,
        'default': DeviceMetricSerializer
    }
    
    permission_classes = [IsAuthenticated, IsActiveUser, HasAPIAccess]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_class = DeviceMetricFilter
    search_fields = ['device__name', 'device__hostname']
    ordering_fields = ['collected_at', 'cpu_usage', 'memory_usage', 'response_time']
    ordering = ['-collected_at']
    
    def get_serializer_class(self):
        return self.serializer_classes.get(self.action, self.serializer_classes['default'])
    
    def get_queryset(self):
        user = self.request.user
        
        if not user or not user.is_authenticated:
            return DeviceMetric.objects.none()
        
        if hasattr(user, 'role') and user.role in ['superadmin', 'admin']:
            return DeviceMetric.objects.all()
        
        # Les utilisateurs normaux voient les métriques des équipements auxquels ils ont accès
        from apps.inventory.models import Device
        accessible_devices = Device.objects.filter(
            Q(owner=user) | Q(tenant__contacts__user=user)
        ).distinct()
        
        return DeviceMetric.objects.filter(device__in=accessible_devices)
    
    @action(detail=False, methods=['get'])
    def latest(self, request):
        """Récupère les dernières métriques pour chaque équipement"""
        from django.db.models import Subquery, OuterRef

        # Récupérer l'utilisateur de la requête
        user = request.user  # ← AJOUTEZ CETTE LIGNE
        
        # Sous-requête pour obtenir la dernière métrique de chaque équipement
        latest_ids = DeviceMetric.objects.filter(
            device=OuterRef('device')
        ).order_by('-collected_at').values('id')[:1]
        
        latest_metrics = DeviceMetric.objects.filter(
            id__in=Subquery(latest_ids)
        ).select_related('device')
        
        # Filtrer selon les permissions
        if not (hasattr(user, 'role') and user.role in ['superadmin', 'admin']):
            from apps.inventory.models import Device
            accessible_devices = Device.objects.filter(
                Q(owner=user) | Q(tenant__contacts__user=user)
            ).distinct()
            latest_metrics = latest_metrics.filter(device__in=accessible_devices)
        
        page = self.paginate_queryset(latest_metrics)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(latest_metrics, many=True)
        return success_response(serializer.data, "Latest metrics retrieved")


# ============================================================================
# MÉTRIQUES DES INTERFACES
# ============================================================================

class InterfaceMetricViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet pour les métriques des interfaces (lecture seule)"""
    
    queryset = InterfaceMetric.objects.select_related('interface', 'interface__device').all()
    serializer_class = InterfaceMetricSerializer
    serializer_classes = {
        'retrieve': InterfaceMetricDetailSerializer,
        'default': InterfaceMetricSerializer
    }
    
    permission_classes = [IsAuthenticated, IsActiveUser, HasAPIAccess]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_class = InterfaceMetricFilter
    search_fields = ['interface__name', 'interface__device__name']
    ordering_fields = ['collected_at', 'rx_rate_bps', 'tx_rate_bps', 'rx_errors', 'tx_errors']
    ordering = ['-collected_at']
    
    def get_serializer_class(self):
        return self.serializer_classes.get(self.action, self.serializer_classes['default'])
    
    def get_queryset(self):
        user = self.request.user
        
        if not user or not user.is_authenticated:
            return InterfaceMetric.objects.none()
        
        if hasattr(user, 'role') and user.role in ['superadmin', 'admin']:
            return InterfaceMetric.objects.all()
        
        # Les utilisateurs normaux voient les métriques des interfaces des équipements accessibles
        from apps.inventory.models import Device
        accessible_devices = Device.objects.filter(
            Q(owner=user) | Q(tenant__contacts__user=user)
        ).distinct()
        
        return InterfaceMetric.objects.filter(interface__device__in=accessible_devices)


# ============================================================================
# MÉTRIQUES APPLICATIVES
# ============================================================================

class ApplicationMetricViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet pour les métriques applicatives (lecture seule)"""
    
    queryset = ApplicationMetric.objects.all()
    serializer_class = ApplicationMetricSerializer
    serializer_classes = {
        'retrieve': ApplicationMetricDetailSerializer,
        'default': ApplicationMetricSerializer
    }
    
    permission_classes = [IsAuthenticated, IsActiveUser, HasAPIAccess]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_class = ApplicationMetricFilter
    search_fields = ['metric_name']
    ordering_fields = ['collected_at', 'metric_value']
    ordering = ['-collected_at']
    
    def get_serializer_class(self):
        return self.serializer_classes.get(self.action, self.serializer_classes['default'])
    
    def get_queryset(self):
        user = self.request.user
        
        if not user or not user.is_authenticated:
            return ApplicationMetric.objects.none()
        
        # Tout le monde peut voir les métriques applicatives
        return ApplicationMetric.objects.all()
    
    @action(detail=False, methods=['post'])
    def query(self, request):
        """Requête avancée de métriques avec agrégation"""
        serializer = MetricQuerySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        
        queryset = ApplicationMetric.objects.all()
        
        # Filtres
        if data.get('metric_type'):
            queryset = queryset.filter(metric_type=data['metric_type'])
        
        if data.get('metric_name'):
            queryset = queryset.filter(metric_name__icontains=data['metric_name'])
        
        if data.get('start_time'):
            queryset = queryset.filter(collected_at__gte=data['start_time'])
        
        if data.get('end_time'):
            queryset = queryset.filter(collected_at__lte=data['end_time'])
        
        # Agrégation par intervalle (à implémenter selon les besoins)
        # Pour l'instant, retourner les métriques brutes
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return success_response(serializer.data, "Metrics retrieved")


# ============================================================================
# ALERTES
# ============================================================================

class AlertViewSet(viewsets.ModelViewSet):
    """ViewSet pour les alertes"""
    
    queryset = Alert.objects.select_related('device', 'interface', 'acknowledged_by').all()
    serializer_class = AlertSerializer
    serializer_classes = {
        'retrieve': AlertDetailSerializer,
        'default': AlertSerializer
    }
    
    permission_classes = [IsAuthenticated, IsActiveUser, HasAPIAccess]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_class = AlertFilter
    search_fields = ['name', 'description']
    ordering_fields = ['last_occurrence', 'severity', 'occurrence_count']
    ordering = ['-last_occurrence']
    
    def get_serializer_class(self):
        return self.serializer_classes.get(self.action, self.serializer_classes['default'])
    
    def get_queryset(self):
        user = self.request.user
        
        if not user or not user.is_authenticated:
            return Alert.objects.none()
        
        if hasattr(user, 'role') and user.role in ['superadmin', 'admin']:
            return Alert.objects.all()
        
        # Les utilisateurs normaux voient les alertes des équipements auxquels ils ont accès
        from apps.inventory.models import Device
        accessible_devices = Device.objects.filter(
            Q(owner=user) | Q(tenant__contacts__user=user)
        ).distinct()
        
        return Alert.objects.filter(
            Q(device__isnull=True) | Q(device__in=accessible_devices)
        )
    
    @action(detail=True, methods=['post'])
    def acknowledge(self, request, pk=None):
        """Acquitter une alerte"""
        alert = self.get_object()
        
        if not self._can_acknowledge(alert):
            self.permission_denied(request)
        
        serializer = AlertAcknowledgeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        alert.acknowledge(request.user)
        if serializer.validated_data.get('notes'):
            alert.notes = serializer.validated_data['notes']
            alert.save()
        
        return success_response(
            AlertDetailSerializer(alert).data,
            "Alert acknowledged"
        )
    
    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """Résoudre une alerte"""
        alert = self.get_object()
        
        if not self._can_resolve(alert):
            self.permission_denied(request)
        
        alert.resolve()
        
        return success_response(
            AlertDetailSerializer(alert).data,
            "Alert resolved"
        )
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Résumé des alertes"""
        queryset = self.get_queryset()
        
        # Alertes actives
        active = queryset.filter(status='active')
        
        summary = {
            'total': queryset.count(),
            'by_severity': dict(queryset.values_list('severity').annotate(count=Count('id'))),
            'by_status': dict(queryset.values_list('status').annotate(count=Count('id'))),
            'by_source': dict(queryset.values_list('source').annotate(count=Count('id'))),
            'active_critical': active.filter(severity='critical').count(),
            'active_high': active.filter(severity='high').count(),
            'active_medium': active.filter(severity='medium').count(),
            'active_low': active.filter(severity='low').count(),
        }
        
        return success_response(summary, "Alert summary retrieved")
    
    def _can_acknowledge(self, alert):
        user = self.request.user
        if not user or not user.is_authenticated:
            return False
        
        if hasattr(user, 'role') and user.role in ['superadmin', 'admin']:
            return True
        
        # Les utilisateurs peuvent acquitter les alertes des équipements auxquels ils ont accès
        if alert.device:
            from apps.inventory.models import Device
            return Device.objects.filter(
                Q(id=alert.device.id) & (Q(owner=user) | Q(tenant__contacts__user=user))
            ).exists()
        
        return False
    
    def _can_resolve(self, alert):
        return self._can_acknowledge(alert)


# ============================================================================
# SEUILS D'ALERTE
# ============================================================================

class AlertThresholdViewSet(viewsets.ModelViewSet):
    """ViewSet pour les seuils d'alerte"""
    
    queryset = AlertThreshold.objects.prefetch_related('devices').all()
    serializer_class = AlertThresholdSerializer
    serializer_classes = {
        'retrieve': AlertThresholdDetailSerializer,
        'default': AlertThresholdSerializer
    }
    
    permission_classes = [IsAuthenticated, IsActiveUser, HasAPIAccess, IsAdmin]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_class = AlertThresholdFilter
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    def get_serializer_class(self):
        return self.serializer_classes.get(self.action, self.serializer_classes['default'])
    
    def get_queryset(self):
        user = self.request.user
        
        if not user or not user.is_authenticated:
            return AlertThreshold.objects.none()
        
        if hasattr(user, 'role') and user.role in ['superadmin', 'admin']:
            return AlertThreshold.objects.all()
        
        return AlertThreshold.objects.filter(created_by=user)
    
    def perform_create(self, serializer):
        if self.request.user.is_authenticated:
            serializer.save(created_by=self.request.user)
        else:
            serializer.save()


# ============================================================================
# CANAUX DE NOTIFICATION
# ============================================================================

class NotificationChannelViewSet(viewsets.ModelViewSet):
    """ViewSet pour les canaux de notification"""
    
    queryset = NotificationChannel.objects.all()
    serializer_class = NotificationChannelSerializer
    permission_classes = [IsAuthenticated, IsActiveUser, HasAPIAccess, IsAdmin]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_class = NotificationChannelFilter
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    def get_queryset(self):
        user = self.request.user
        
        if not user or not user.is_authenticated:
            return NotificationChannel.objects.none()
        
        if hasattr(user, 'role') and user.role in ['superadmin', 'admin']:
            return NotificationChannel.objects.all()
        
        return NotificationChannel.objects.none()  # Seuls les admins peuvent voir


# ============================================================================
# LOGS DE NOTIFICATION
# ============================================================================

class NotificationLogViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet pour les logs de notification (lecture seule)"""
    
    queryset = NotificationLog.objects.select_related('alert', 'channel').all()
    serializer_class = NotificationLogSerializer
    permission_classes = [IsAuthenticated, IsActiveUser, HasAPIAccess, IsAdmin]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_class = NotificationLogFilter
    ordering_fields = ['sent_at']
    ordering = ['-sent_at']
    
    def get_queryset(self):
        user = self.request.user
        
        if not user or not user.is_authenticated:
            return NotificationLog.objects.none()
        
        if hasattr(user, 'role') and user.role in ['superadmin', 'admin']:
            return NotificationLog.objects.all()
        
        return NotificationLog.objects.none()  # Seuls les admins peuvent voir


# ============================================================================
# TABLEAUX DE BORD
# ============================================================================

class DashboardViewSet(viewsets.ModelViewSet):
    """ViewSet pour les tableaux de bord"""
    
    queryset = Dashboard.objects.select_related('owner').all()
    serializer_class = DashboardSerializer
    serializer_classes = {
        'retrieve': DashboardDetailSerializer,
        'default': DashboardSerializer
    }
    
    permission_classes = [IsAuthenticated, IsActiveUser, HasAPIAccess]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_class = DashboardFilter
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    def get_serializer_class(self):
        return self.serializer_classes.get(self.action, self.serializer_classes['default'])
    
    def get_queryset(self):
        user = self.request.user
        
        if not user or not user.is_authenticated:
            return Dashboard.objects.none()
        
        if hasattr(user, 'role') and user.role in ['superadmin', 'admin']:
            return Dashboard.objects.all()
        
        return Dashboard.objects.filter(
            Q(owner=user) | Q(is_public=True)
        ).distinct()
    
    def perform_create(self, serializer):
        if self.request.user.is_authenticated:
            serializer.save(owner=self.request.user)
        else:
            serializer.save()


# ============================================================================
# COLLECTIONS DE MÉTRIQUES
# ============================================================================

class MetricCollectionViewSet(viewsets.ModelViewSet):
    """ViewSet pour les collections de métriques"""
    
    queryset = MetricCollection.objects.all()
    serializer_class = MetricCollectionSerializer
    permission_classes = [IsAuthenticated, IsActiveUser, HasAPIAccess, IsAdmin]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_class = MetricCollectionFilter
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    def get_queryset(self):
        user = self.request.user
        
        if not user or not user.is_authenticated:
            return MetricCollection.objects.none()
        
        if hasattr(user, 'role') and user.role in ['superadmin', 'admin']:
            return MetricCollection.objects.all()
        
        return MetricCollection.objects.all()  # Tout le monde peut voir les collections


# ============================================================================
# DASHBOARD PRINCIPAL
# ============================================================================

class MonitoringDashboardViewSet(viewsets.ViewSet):
    """Dashboard principal pour le monitoring"""
    permission_classes = [IsAuthenticated, IsActiveUser, HasAPIAccess]
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Résumé de toutes les métriques"""
        user = request.user
        
        if not user or not user.is_authenticated:
            return error_response("Authentication required")
        
        # Dernières 24h
        last_24h = timezone.now() - timedelta(hours=24)
        
        # Statistiques système
        system_metrics = SystemMetric.objects.filter(collected_at__gte=last_24h)
        latest_system = SystemMetric.objects.order_by('-collected_at').first()
        
        # Statistiques des équipements
        if hasattr(user, 'role') and user.role in ['superadmin', 'admin']:
            devices_total = DeviceMetric.objects.values('device').distinct().count()
            devices_online = DeviceMetric.objects.filter(
                is_reachable=True, collected_at__gte=last_24h
            ).values('device').distinct().count()
        else:
            from apps.inventory.models import Device
            accessible_devices = Device.objects.filter(
                Q(owner=user) | Q(tenant__contacts__user=user)
            ).distinct()
            devices_total = accessible_devices.count()
            devices_online = DeviceMetric.objects.filter(
                device__in=accessible_devices,
                is_reachable=True,
                collected_at__gte=last_24h
            ).values('device').distinct().count()
        
        # Statistiques des alertes
        alerts = Alert.objects.all()
        if not (hasattr(user, 'role') and user.role in ['superadmin', 'admin']):
            from apps.inventory.models import Device
            accessible_devices = Device.objects.filter(
                Q(owner=user) | Q(tenant__contacts__user=user)
            ).distinct()
            alerts = alerts.filter(
                Q(device__isnull=True) | Q(device__in=accessible_devices)
            )
        
        active_alerts = alerts.filter(status='active')
        
        # Statistiques applicatives
        app_metrics = ApplicationMetric.objects.filter(collected_at__gte=last_24h)
        
        data = {
            'system': {
                'latest_cpu': latest_system.cpu_usage if latest_system else None,
                'latest_memory': latest_system.memory_percent if latest_system else None,
                'latest_disk': latest_system.disk_percent if latest_system else None,
                'avg_cpu_24h': system_metrics.aggregate(avg=Avg('cpu_usage'))['avg'],
                'avg_memory_24h': system_metrics.aggregate(avg=Avg('memory_percent'))['avg'],
                'avg_disk_24h': system_metrics.aggregate(avg=Avg('disk_percent'))['avg'],
                'metrics_count_24h': system_metrics.count(),
            },
            'devices': {
                'total': devices_total,
                'online': devices_online,
                'offline': devices_total - devices_online,
                'online_percentage': (devices_online / devices_total * 100) if devices_total > 0 else 0,
            },
            'applications': {
                'ansible_executions': app_metrics.filter(metric_type='ansible').count(),
                'terraform_applies': app_metrics.filter(metric_type='terraform').count(),
                'jenkins_builds': app_metrics.filter(metric_type='jenkins').count(),
                'grafana_dashboards': app_metrics.filter(metric_type='grafana').count(),
                'eveng_labs': app_metrics.filter(metric_type='eveng').count(),
            },
            'alerts': {
                'total': alerts.count(),
                'active': active_alerts.count(),
                'by_severity': dict(active_alerts.values_list('severity').annotate(count=Count('id'))),
                'latest': AlertSerializer(active_alerts.order_by('-last_occurrence')[:5], many=True).data,
            }
        }
        
        return success_response(data, "Monitoring summary retrieved")
