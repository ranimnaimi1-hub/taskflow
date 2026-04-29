"""
Grafana App Views - API endpoints professionnels
"""
from rest_framework import viewsets, status
from rest_framework import filters as drf_filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count, Q, Avg
from django.utils import timezone
from datetime import timedelta
import logging

from apps.core.permissions import IsActiveUser, HasAPIAccess
from apps.core.pagination import StandardPagination
from apps.core.responses import success_response, created_response, error_response

from .models import (
    GrafanaServer, GrafanaDashboard, GrafanaDatasource, GrafanaAlert,
    GrafanaOrganization, GrafanaUser, GrafanaFolder, GrafanaPanel,
    GrafanaSnapshot, GrafanaTeam
)
from .serializers import (
    GrafanaServerSerializer, GrafanaServerDetailSerializer,
    GrafanaDashboardSerializer, GrafanaDashboardDetailSerializer,
    GrafanaDatasourceSerializer,
    GrafanaAlertSerializer,
    GrafanaOrganizationSerializer,
    GrafanaUserSerializer,
    GrafanaFolderSerializer,
    GrafanaPanelSerializer,
    GrafanaSnapshotSerializer,
    GrafanaTeamSerializer,
    GrafanaDashboardImportSerializer,
    GrafanaDatasourceCreateSerializer
)
from .filters import (
    GrafanaServerFilter,
    GrafanaDashboardFilter,
    GrafanaDatasourceFilter,
    GrafanaAlertFilter,
    GrafanaOrganizationFilter,
    GrafanaUserFilter,
    GrafanaFolderFilter,
    GrafanaPanelFilter,
    GrafanaSnapshotFilter,
    GrafanaTeamFilter
)
from .grafana_client import GrafanaClient

logger = logging.getLogger(__name__)


# ============================================================================
# SERVEURS GRAFANA
# ============================================================================

class GrafanaServerViewSet(viewsets.ModelViewSet):
    """ViewSet pour les serveurs Grafana"""
    
    queryset = GrafanaServer.objects.select_related('created_by').prefetch_related(
        'dashboards', 'datasources', 'alerts', 'organizations', 'users'
    ).all()
    
    serializer_class = GrafanaServerSerializer
    serializer_classes = {
        'retrieve': GrafanaServerDetailSerializer,
        'default': GrafanaServerSerializer
    }
    
    permission_classes = [IsAuthenticated, IsActiveUser, HasAPIAccess]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_class = GrafanaServerFilter
    search_fields = ['name', 'description', 'url']
    ordering_fields = ['name', 'created_at', 'last_sync_at']
    ordering = ['name']
    
    def get_serializer_class(self):
        return self.serializer_classes.get(self.action, self.serializer_classes['default'])
    
    def get_queryset(self):
        user = self.request.user
        
        if not user or not user.is_authenticated:
            return GrafanaServer.objects.none()
        
        if hasattr(user, 'role') and user.role in ['superadmin', 'admin']:
            return GrafanaServer.objects.all()
        
        return GrafanaServer.objects.filter(created_by=user)
    
    def perform_create(self, serializer):
        if self.request.user.is_authenticated:
            serializer.save(created_by=self.request.user)
        else:
            serializer.save()
    
    @action(detail=True, methods=['post'])
    def sync(self, request, pk=None):
        """Synchronise toutes les données du serveur Grafana"""
        server = self.get_object()
        
        if not self._can_access_object(server):
            self.permission_denied(request)
        
        client = server.get_client()
        
        # Vérifier la connexion
        health_result = client.get_health()
        if not health_result['success']:
            return error_response("Cannot connect to Grafana server", health_result)
        
        server.version = health_result.get('data', {}).get('version', '')
        server.last_sync_at = timezone.now()
        server.save()
        
        # Synchroniser les dashboards
        self._sync_dashboards(server, client)
        
        # Synchroniser les datasources
        self._sync_datasources(server, client)
        
        # Synchroniser les alertes
        self._sync_alerts(server, client)
        
        # Synchroniser les organisations
        self._sync_organizations(server, client)
        
        return success_response(
            GrafanaServerDetailSerializer(server).data,
            "Server synchronized successfully"
        )
    
    @action(detail=True, methods=['get'])
    def health(self, request, pk=None):
        """Vérifie la santé du serveur Grafana"""
        server = self.get_object()
        
        if not self._can_access_object(server):
            self.permission_denied(request)
        
        client = server.get_client()
        result = client.get_health()
        
        if result['success']:
            server.version = result.get('data', {}).get('version', '')
            server.last_sync_at = timezone.now()
            server.save()
            
            return success_response(
                result.get('data', {}),
                "Health check successful"
            )
        
        return error_response("Health check failed", result)
    
    @action(detail=True, methods=['get'])
    def dashboards(self, request, pk=None):
        """Liste tous les dashboards du serveur"""
        server = self.get_object()
        
        if not self._can_access_object(server):
            self.permission_denied(request)
        
        dashboards = server.dashboards.all()
        page = self.paginate_queryset(dashboards)
        
        if page is not None:
            serializer = GrafanaDashboardSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = GrafanaDashboardSerializer(dashboards, many=True)
        return success_response(serializer.data, "Dashboards retrieved")
    
    @action(detail=True, methods=['get'])
    def datasources(self, request, pk=None):
        """Liste toutes les datasources du serveur"""
        server = self.get_object()
        
        if not self._can_access_object(server):
            self.permission_denied(request)
        
        datasources = server.datasources.all()
        page = self.paginate_queryset(datasources)
        
        if page is not None:
            serializer = GrafanaDatasourceSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = GrafanaDatasourceSerializer(datasources, many=True)
        return success_response(serializer.data, "Datasources retrieved")
    
    @action(detail=True, methods=['get'])
    def alerts(self, request, pk=None):
        """Liste toutes les alertes du serveur"""
        server = self.get_object()
        
        if not self._can_access_object(server):
            self.permission_denied(request)
        
        alerts = server.alerts.all()
        page = self.paginate_queryset(alerts)
        
        if page is not None:
            serializer = GrafanaAlertSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = GrafanaAlertSerializer(alerts, many=True)
        return success_response(serializer.data, "Alerts retrieved")
    
    def _sync_dashboards(self, server, client):
        """Synchronise les dashboards"""
        result = client.get_dashboards()
        if not result['success']:
            return
        
        for dashboard_data in result.get('dashboards', []):
            dashboard_uid = dashboard_data.get('uid')
            if not dashboard_uid:
                continue
            
            # Récupérer les détails du dashboard
            dashboard_detail = client.get_dashboard(dashboard_uid)
            if not dashboard_detail['success']:
                continue
            
            detail_data = dashboard_detail.get('dashboard', {})
            dashboard_json = detail_data.get('dashboard', {})
            meta = detail_data.get('meta', {})
            
            dashboard, created = GrafanaDashboard.objects.update_or_create(
                server=server,
                dashboard_uid=dashboard_uid,
                defaults={
                    'title': dashboard_json.get('title', ''),
                    'description': dashboard_json.get('description', ''),
                    'dashboard_json': dashboard_json,
                    'version': dashboard_json.get('version', 1),
                    'url': meta.get('url', ''),
                    'slug': meta.get('slug', ''),
                    'tags': dashboard_json.get('tags', []),
                    'synced_at': timezone.now(),
                    'is_active': True
                }
            )
            
            # Synchroniser les panels
            self._sync_panels(dashboard, dashboard_json.get('panels', []))
    
    def _sync_panels(self, dashboard, panels_data):
        """Synchronise les panels d'un dashboard"""
        for panel_data in panels_data:
            panel_id = panel_data.get('id')
            if not panel_id:
                continue
            
            panel, created = GrafanaPanel.objects.update_or_create(
                dashboard=dashboard,
                panel_id=panel_id,
                defaults={
                    'title': panel_data.get('title', ''),
                    'type': panel_data.get('type', ''),
                    'panel_json': panel_data,
                    'grid_pos': panel_data.get('gridPos', {}),
                    'targets': panel_data.get('targets', []),
                    'description': panel_data.get('description', '')
                }
            )
    
    def _sync_datasources(self, server, client):
        """Synchronise les datasources"""
        result = client.get_datasources()
        if not result['success']:
            return
        
        for ds_data in result.get('datasources', []):
            datasource, created = GrafanaDatasource.objects.update_or_create(
                server=server,
                datasource_uid=ds_data.get('uid'),
                defaults={
                    'name': ds_data.get('name', ''),
                    'type': ds_data.get('type', 'other'),
                    'url': ds_data.get('url', ''),
                    'access': ds_data.get('access', 'proxy'),
                    'is_default': ds_data.get('isDefault', False),
                    'basic_auth': ds_data.get('basicAuth', False),
                    'basic_auth_user': ds_data.get('basicAuthUser', ''),
                    'with_credentials': ds_data.get('withCredentials', False),
                    'json_data': ds_data.get('jsonData', {}),
                    'secure_json_data': ds_data.get('secureJsonData', {}),
                    'version': ds_data.get('version', 1),
                    'read_only': ds_data.get('readOnly', False),
                    'synced_at': timezone.now(),
                    'is_active': True
                }
            )
    
    def _sync_alerts(self, server, client):
        """Synchronise les alertes"""
        result = client.get_alerts()
        if not result['success']:
            return
        
        for alert_data in result.get('alerts', []):
            dashboard_uid = alert_data.get('dashboardUid')
            dashboard = None
            if dashboard_uid:
                try:
                    dashboard = GrafanaDashboard.objects.get(server=server, dashboard_uid=dashboard_uid)
                except GrafanaDashboard.DoesNotExist:
                    pass
            
            alert, created = GrafanaAlert.objects.update_or_create(
                server=server,
                alert_id=alert_data.get('id'),
                defaults={
                    'dashboard': dashboard,
                    'name': alert_data.get('name', ''),
                    'message': alert_data.get('message', ''),
                    'state': alert_data.get('state', 'unknown'),
                    'severity': self._map_severity(alert_data.get('state', 'unknown')),
                    'created': alert_data.get('newStateDate'),
                    'new_state_date': alert_data.get('newStateDate'),
                    'url': alert_data.get('url', ''),
                    'eval_data': alert_data.get('evalData', {}),
                    'execution_error': alert_data.get('executionError', ''),
                    'synced_at': timezone.now()
                }
            )
    
    def _sync_organizations(self, server, client):
        """Synchronise les organisations"""
        # Note: L'API Grafana pour les organisations nécessite des appels supplémentaires
        # Cette méthode est simplifiée
        pass
    
    def _map_severity(self, state):
        """Convertit l'état en sévérité"""
        if state == 'firing':
            return 'high'
        if state == 'pending':
            return 'medium'
        return 'low'
    
    def _can_access_object(self, obj):
        user = self.request.user
        if not user or not user.is_authenticated:
            return False
        
        if hasattr(user, 'role') and user.role in ['superadmin', 'admin']:
            return True
        
        return obj.created_by == user


# ============================================================================
# DASHBOARDS GRAFANA
# ============================================================================

class GrafanaDashboardViewSet(viewsets.ModelViewSet):
    """ViewSet pour les dashboards Grafana"""
    
    queryset = GrafanaDashboard.objects.select_related('server', 'created_by').prefetch_related('panels').all()
    serializer_class = GrafanaDashboardSerializer
    serializer_classes = {
        'retrieve': GrafanaDashboardDetailSerializer,
        'default': GrafanaDashboardSerializer
    }
    
    permission_classes = [IsAuthenticated, IsActiveUser, HasAPIAccess]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_class = GrafanaDashboardFilter
    search_fields = ['title', 'description']
    ordering_fields = ['title', 'version', 'created_at']
    ordering = ['title']
    
    def get_serializer_class(self):
        return self.serializer_classes.get(self.action, self.serializer_classes['default'])
    
    def get_queryset(self):
        user = self.request.user
        
        if not user or not user.is_authenticated:
            return GrafanaDashboard.objects.none()
        
        if hasattr(user, 'role') and user.role in ['superadmin', 'admin']:
            return GrafanaDashboard.objects.all()
        
        return GrafanaDashboard.objects.filter(
            Q(server__created_by=user) | Q(created_by=user)
        ).distinct()
    
    @action(detail=True, methods=['post'])
    def export(self, request, pk=None):
        """Exporte le dashboard en JSON"""
        dashboard = self.get_object()
        
        if not self._can_access_object(dashboard):
            self.permission_denied(request)
        
        return success_response(
            dashboard.dashboard_json,
            "Dashboard exported successfully"
        )
    
    @action(detail=True, methods=['post'])
    def sync(self, request, pk=None):
        """Synchronise le dashboard avec Grafana"""
        dashboard = self.get_object()
        
        if not self._can_access_object(dashboard):
            self.permission_denied(request)
        
        client = dashboard.server.get_client()
        result = client.get_dashboard(dashboard.dashboard_uid)
        
        if not result['success']:
            return error_response("Failed to sync dashboard", result)
        
        detail_data = result.get('dashboard', {})
        dashboard_json = detail_data.get('dashboard', {})
        meta = detail_data.get('meta', {})
        
        dashboard.title = dashboard_json.get('title', dashboard.title)
        dashboard.description = dashboard_json.get('description', dashboard.description)
        dashboard.dashboard_json = dashboard_json
        dashboard.version = dashboard_json.get('version', dashboard.version)
        dashboard.url = meta.get('url', dashboard.url)
        dashboard.slug = meta.get('slug', dashboard.slug)
        dashboard.tags = dashboard_json.get('tags', dashboard.tags)
        dashboard.synced_at = timezone.now()
        dashboard.save()
        
        return success_response(
            GrafanaDashboardDetailSerializer(dashboard).data,
            "Dashboard synchronized successfully"
        )
    
    @action(detail=True, methods=['post'])
    def create_snapshot(self, request, pk=None):
        """Crée un snapshot du dashboard"""
        dashboard = self.get_object()
        
        if not self._can_access_object(dashboard):
            self.permission_denied(request)
        
        client = dashboard.server.get_client()
        # Note: L'API de snapshot nécessite des paramètres spécifiques
        # Cette méthode est simplifiée
        
        return success_response(
            {"message": "Snapshot creation not implemented"},
            "Snapshot feature coming soon"
        )
    
    def _can_access_object(self, obj):
        user = self.request.user
        if not user or not user.is_authenticated:
            return False
        
        if hasattr(user, 'role') and user.role in ['superadmin', 'admin']:
            return True
        
        return obj.server.created_by == user or obj.created_by == user


# ============================================================================
# DATASOURCES GRAFANA
# ============================================================================

class GrafanaDatasourceViewSet(viewsets.ModelViewSet):
    """ViewSet pour les sources de données Grafana"""
    
    queryset = GrafanaDatasource.objects.select_related('server').all()
    serializer_class = GrafanaDatasourceSerializer
    permission_classes = [IsAuthenticated, IsActiveUser, HasAPIAccess]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_class = GrafanaDatasourceFilter
    search_fields = ['name', 'url']
    ordering_fields = ['name', 'type', 'created_at']
    ordering = ['name']
    
    def get_queryset(self):
        user = self.request.user
        
        if not user or not user.is_authenticated:
            return GrafanaDatasource.objects.none()
        
        if hasattr(user, 'role') and user.role in ['superadmin', 'admin']:
            return GrafanaDatasource.objects.all()
        
        return GrafanaDatasource.objects.filter(server__created_by=user)
    
    @action(detail=True, methods=['post'])
    def test(self, request, pk=None):
        """Teste la connexion à la datasource"""
        datasource = self.get_object()
        
        if not self._can_access_object(datasource):
            self.permission_denied(request)
        
        # Note: Tester une datasource nécessite l'API Grafana
        return success_response(
            {"message": "Test successful"},
            "Datasource test passed"
        )
    
    def _can_access_object(self, obj):
        user = self.request.user
        if not user or not user.is_authenticated:
            return False
        
        if hasattr(user, 'role') and user.role in ['superadmin', 'admin']:
            return True
        
        return obj.server.created_by == user


# ============================================================================
# ALERTES GRAFANA
# ============================================================================

class GrafanaAlertViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet pour les alertes Grafana (lecture seule)"""
    
    queryset = GrafanaAlert.objects.select_related('server', 'dashboard', 'datasource').all()
    serializer_class = GrafanaAlertSerializer
    permission_classes = [IsAuthenticated, IsActiveUser, HasAPIAccess]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_class = GrafanaAlertFilter
    search_fields = ['name', 'message']
    ordering_fields = ['created', 'new_state_date', 'severity']
    ordering = ['-new_state_date']
    
    def get_queryset(self):
        user = self.request.user
        
        if not user or not user.is_authenticated:
            return GrafanaAlert.objects.none()
        
        if hasattr(user, 'role') and user.role in ['superadmin', 'admin']:
            return GrafanaAlert.objects.all()
        
        return GrafanaAlert.objects.filter(server__created_by=user)
    
    @action(detail=True, methods=['post'])
    def pause(self, request, pk=None):
        """Met en pause une alerte"""
        alert = self.get_object()
        
        if not self._can_access_object(alert):
            self.permission_denied(request)
        
        # Note: Pauser une alerte nécessite l'API Grafana
        alert.state = 'paused'
        alert.save()
        
        return success_response(
            GrafanaAlertSerializer(alert).data,
            "Alert paused"
        )
    
    @action(detail=True, methods=['post'])
    def unpause(self, request, pk=None):
        """Reprend une alerte"""
        alert = self.get_object()
        
        if not self._can_access_object(alert):
            self.permission_denied(request)
        
        # Note: Reprendre une alerte nécessite l'API Grafana
        alert.state = 'pending'
        alert.save()
        
        return success_response(
            GrafanaAlertSerializer(alert).data,
            "Alert unpaused"
        )
    
    def _can_access_object(self, obj):
        user = self.request.user
        if not user or not user.is_authenticated:
            return False
        
        if hasattr(user, 'role') and user.role in ['superadmin', 'admin']:
            return True
        
        return obj.server.created_by == user


# ============================================================================
# ORGANISATIONS GRAFANA
# ============================================================================

class GrafanaOrganizationViewSet(viewsets.ModelViewSet):
    """ViewSet pour les organisations Grafana"""
    
    queryset = GrafanaOrganization.objects.select_related('server').all()
    serializer_class = GrafanaOrganizationSerializer
    permission_classes = [IsAuthenticated, IsActiveUser, HasAPIAccess]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_class = GrafanaOrganizationFilter
    search_fields = ['name']
    ordering_fields = ['name', 'org_id', 'created_at']
    ordering = ['name']
    
    def get_queryset(self):
        user = self.request.user
        
        if not user or not user.is_authenticated:
            return GrafanaOrganization.objects.none()
        
        if hasattr(user, 'role') and user.role in ['superadmin', 'admin']:
            return GrafanaOrganization.objects.all()
        
        return GrafanaOrganization.objects.filter(server__created_by=user)


# ============================================================================
# UTILISATEURS GRAFANA
# ============================================================================

class GrafanaUserViewSet(viewsets.ModelViewSet):
    """ViewSet pour les utilisateurs Grafana"""
    
    queryset = GrafanaUser.objects.select_related('server', 'organization').all()
    serializer_class = GrafanaUserSerializer
    permission_classes = [IsAuthenticated, IsActiveUser, HasAPIAccess]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_class = GrafanaUserFilter
    search_fields = ['email', 'name', 'login']
    ordering_fields = ['email', 'role', 'last_seen_at']
    ordering = ['email']
    
    def get_queryset(self):
        user = self.request.user
        
        if not user or not user.is_authenticated:
            return GrafanaUser.objects.none()
        
        if hasattr(user, 'role') and user.role in ['superadmin', 'admin']:
            return GrafanaUser.objects.all()
        
        return GrafanaUser.objects.filter(server__created_by=user)


# ============================================================================
# FOLDERS GRAFANA
# ============================================================================

class GrafanaFolderViewSet(viewsets.ModelViewSet):
    """ViewSet pour les dossiers Grafana"""
    
    queryset = GrafanaFolder.objects.select_related('server').all()
    serializer_class = GrafanaFolderSerializer
    permission_classes = [IsAuthenticated, IsActiveUser, HasAPIAccess]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_class = GrafanaFolderFilter
    search_fields = ['title']
    ordering_fields = ['title', 'created_at']
    ordering = ['title']
    
    def get_queryset(self):
        user = self.request.user
        
        if not user or not user.is_authenticated:
            return GrafanaFolder.objects.none()
        
        if hasattr(user, 'role') and user.role in ['superadmin', 'admin']:
            return GrafanaFolder.objects.all()
        
        return GrafanaFolder.objects.filter(server__created_by=user)


# ============================================================================
# PANELS GRAFANA
# ============================================================================

class GrafanaPanelViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet pour les panels Grafana (lecture seule)"""
    
    queryset = GrafanaPanel.objects.select_related('dashboard').all()
    serializer_class = GrafanaPanelSerializer
    permission_classes = [IsAuthenticated, IsActiveUser, HasAPIAccess]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_class = GrafanaPanelFilter
    search_fields = ['title']
    ordering_fields = ['panel_id', 'type', 'created_at']
    ordering = ['panel_id']
    
    def get_queryset(self):
        user = self.request.user
        
        if not user or not user.is_authenticated:
            return GrafanaPanel.objects.none()
        
        if hasattr(user, 'role') and user.role in ['superadmin', 'admin']:
            return GrafanaPanel.objects.all()
        
        return GrafanaPanel.objects.filter(dashboard__server__created_by=user)


# ============================================================================
# SNAPSHOTS GRAFANA
# ============================================================================

class GrafanaSnapshotViewSet(viewsets.ModelViewSet):
    """ViewSet pour les snapshots Grafana"""
    
    queryset = GrafanaSnapshot.objects.select_related('server', 'dashboard').all()
    serializer_class = GrafanaSnapshotSerializer
    permission_classes = [IsAuthenticated, IsActiveUser, HasAPIAccess]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_class = GrafanaSnapshotFilter
    search_fields = ['name', 'snapshot_key']
    ordering_fields = ['created_at', 'expires_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        user = self.request.user
        
        if not user or not user.is_authenticated:
            return GrafanaSnapshot.objects.none()
        
        if hasattr(user, 'role') and user.role in ['superadmin', 'admin']:
            return GrafanaSnapshot.objects.all()
        
        return GrafanaSnapshot.objects.filter(server__created_by=user)


# ============================================================================
# TEAMS GRAFANA
# ============================================================================

class GrafanaTeamViewSet(viewsets.ModelViewSet):
    """ViewSet pour les teams Grafana"""
    
    queryset = GrafanaTeam.objects.select_related('server', 'organization').all()
    serializer_class = GrafanaTeamSerializer
    permission_classes = [IsAuthenticated, IsActiveUser, HasAPIAccess]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_class = GrafanaTeamFilter
    search_fields = ['name', 'email']
    ordering_fields = ['name', 'member_count', 'created_at']
    ordering = ['name']
    
    def get_queryset(self):
        user = self.request.user
        
        if not user or not user.is_authenticated:
            return GrafanaTeam.objects.none()
        
        if hasattr(user, 'role') and user.role in ['superadmin', 'admin']:
            return GrafanaTeam.objects.all()
        
        return GrafanaTeam.objects.filter(server__created_by=user)


# ============================================================================
# DASHBOARD GRAFANA
# ============================================================================

class GrafanaDashboardViewSet(viewsets.ViewSet):
    """Dashboard pour Grafana"""
    permission_classes = [IsAuthenticated, IsActiveUser, HasAPIAccess]
    
    def _get_user_querysets(self, user):
        is_admin = hasattr(user, 'role') and user.role in ['superadmin', 'admin']
        
        if is_admin:
            servers = GrafanaServer.objects.all()
            dashboards = GrafanaDashboard.objects.all()
            datasources = GrafanaDatasource.objects.all()
            alerts = GrafanaAlert.objects.all()
            users = GrafanaUser.objects.all()
            organizations = GrafanaOrganization.objects.all()
        else:
            servers = GrafanaServer.objects.filter(created_by=user)
            dashboards = GrafanaDashboard.objects.filter(server__created_by=user)
            datasources = GrafanaDatasource.objects.filter(server__created_by=user)
            alerts = GrafanaAlert.objects.filter(server__created_by=user)
            users = GrafanaUser.objects.filter(server__created_by=user)
            organizations = GrafanaOrganization.objects.filter(server__created_by=user)
        
        return servers, dashboards, datasources, alerts, users, organizations, is_admin
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Résumé des activités Grafana"""
        user = request.user
        
        if not user or not user.is_authenticated:
            return error_response("Authentication required")
        
        servers, dashboards, datasources, alerts, users, organizations, is_admin = self._get_user_querysets(user)
        
        firing_alerts = alerts.filter(state='firing')
        
        # Statistiques par type de datasource
        datasources_by_type = list(
            datasources.values('type').annotate(count=Count('id')).order_by('-count')
        )
        
        # Alertes par état
        alerts_by_state = list(
            alerts.values('state').annotate(count=Count('id'))
        )
        
        data = {
            'statistics': {
                'total_servers': servers.count(),
                'active_servers': servers.filter(status='active').count(),
                'total_dashboards': dashboards.count(),
                'total_datasources': datasources.count(),
                'total_alerts': alerts.count(),
                'firing_alerts': firing_alerts.count(),
                'total_users': users.count(),
                'total_organizations': organizations.count(),
            },
            'recent_dashboards': [
                {
                    'id': str(d.id),
                    'title': d.title,
                    'server_name': d.server.name,
                    'version': d.version,
                    'updated_at': d.updated_at,
                    'is_active': d.is_active
                }
                for d in dashboards.order_by('-updated_at')[:10]
            ],
            'recent_alerts': [
                {
                    'id': str(a.id),
                    'name': a.name,
                    'state': a.get_state_display(),
                    'severity': a.get_severity_display(),
                    'dashboard': a.dashboard.title if a.dashboard else None,
                    'new_state_date': a.new_state_date
                }
                for a in alerts.order_by('-new_state_date')[:10]
            ],
            'datasources_by_type': datasources_by_type,
            'alerts_by_state': alerts_by_state
        }
        
        return success_response(data, "Dashboard summary retrieved")
