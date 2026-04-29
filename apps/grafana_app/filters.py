"""
Grafana App Filters - Filtres personnalisés pour l'API
"""
import django_filters
from django_filters import rest_framework as filters
from django.db import models
from django.db.models import Q, Count
from .models import (
    GrafanaServer, GrafanaDashboard, GrafanaDatasource, GrafanaAlert,
    GrafanaOrganization, GrafanaUser, GrafanaFolder, GrafanaPanel,
    GrafanaSnapshot, GrafanaTeam
)


# ============================================================================
# FILTRES POUR SERVEURS GRAFANA
# ============================================================================

class GrafanaServerFilter(filters.FilterSet):
    """Filtres pour GrafanaServer"""
    name = filters.CharFilter(lookup_expr='icontains')
    description = filters.CharFilter(lookup_expr='icontains')
    url = filters.CharFilter(lookup_expr='icontains')
    status = filters.ChoiceFilter(choices=GrafanaServer.STATUS_CHOICES)
    
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
    min_dashboards = filters.NumberFilter(method='filter_min_dashboards')
    max_dashboards = filters.NumberFilter(method='filter_max_dashboards')
    min_datasources = filters.NumberFilter(method='filter_min_datasources')
    max_datasources = filters.NumberFilter(method='filter_max_datasources')
    min_alerts = filters.NumberFilter(method='filter_min_alerts')
    max_alerts = filters.NumberFilter(method='filter_max_alerts')
    
    has_version = filters.BooleanFilter(field_name='version', lookup_expr='isnull', exclude=True)
    is_active = filters.BooleanFilter(field_name='status', method='filter_is_active')
    
    class Meta:
        model = GrafanaServer
        fields = ['name', 'status', 'created_by']
    
    def filter_min_dashboards(self, queryset, name, value):
        return queryset.annotate(dashboards_count=Count('dashboards')).filter(dashboards_count__gte=value)
    
    def filter_max_dashboards(self, queryset, name, value):
        return queryset.annotate(dashboards_count=Count('dashboards')).filter(dashboards_count__lte=value)
    
    def filter_min_datasources(self, queryset, name, value):
        return queryset.annotate(datasources_count=Count('datasources')).filter(datasources_count__gte=value)
    
    def filter_max_datasources(self, queryset, name, value):
        return queryset.annotate(datasources_count=Count('datasources')).filter(datasources_count__lte=value)
    
    def filter_min_alerts(self, queryset, name, value):
        return queryset.annotate(alerts_count=Count('alerts')).filter(alerts_count__gte=value)
    
    def filter_max_alerts(self, queryset, name, value):
        return queryset.annotate(alerts_count=Count('alerts')).filter(alerts_count__lte=value)
    
    def filter_is_active(self, queryset, name, value):
        if value:
            return queryset.filter(status='active')
        return queryset.exclude(status='active')


# ============================================================================
# FILTRES POUR DASHBOARDS GRAFANA
# ============================================================================

class GrafanaDashboardFilter(filters.FilterSet):
    """Filtres pour GrafanaDashboard"""
    title = filters.CharFilter(lookup_expr='icontains')
    description = filters.CharFilter(lookup_expr='icontains')
    dashboard_uid = filters.CharFilter(lookup_expr='icontains')
    slug = filters.CharFilter(lookup_expr='icontains')
    is_active = filters.BooleanFilter()
    
    # Server filters
    server = filters.UUIDFilter(field_name='server__id')
    server_name = filters.CharFilter(field_name='server__name', lookup_expr='icontains')
    
    # Version filters
    min_version = filters.NumberFilter(field_name='version', lookup_expr='gte')
    max_version = filters.NumberFilter(field_name='version', lookup_expr='lte')
    
    # Tags filters
    has_tag = filters.CharFilter(method='filter_has_tag')
    tags_contains = filters.CharFilter(method='filter_tags_contains')
    
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
    
    # Panels filters
    min_panels = filters.NumberFilter(method='filter_min_panels')
    max_panels = filters.NumberFilter(method='filter_max_panels')
    
    class Meta:
        model = GrafanaDashboard
        fields = ['title', 'is_active', 'server', 'created_by']
    
    def filter_has_tag(self, queryset, name, value):
        """Filtre les dashboards qui ont un tag spécifique"""
        return queryset.filter(tags__contains=[value])
    
    def filter_tags_contains(self, queryset, name, value):
        """Filtre les dashboards dont les tags contiennent une chaîne"""
        result_ids = []
        for dashboard in queryset:
            if any(value.lower() in tag.lower() for tag in dashboard.tags):
                result_ids.append(dashboard.id)
        return queryset.filter(id__in=result_ids)
    
    def filter_min_panels(self, queryset, name, value):
        return queryset.annotate(panels_count=Count('panels')).filter(panels_count__gte=value)
    
    def filter_max_panels(self, queryset, name, value):
        return queryset.annotate(panels_count=Count('panels')).filter(panels_count__lte=value)


# ============================================================================
# FILTRES POUR DATASOURCES GRAFANA
# ============================================================================

class GrafanaDatasourceFilter(filters.FilterSet):
    """Filtres pour GrafanaDatasource"""
    name = filters.CharFilter(lookup_expr='icontains')
    type = filters.ChoiceFilter(choices=GrafanaDatasource.DATASOURCE_TYPE_CHOICES)
    url = filters.CharFilter(lookup_expr='icontains')
    is_default = filters.BooleanFilter()
    is_active = filters.BooleanFilter()
    read_only = filters.BooleanFilter()
    
    # Server filters
    server = filters.UUIDFilter(field_name='server__id')
    server_name = filters.CharFilter(field_name='server__name', lookup_expr='icontains')
    
    # Version filters
    min_version = filters.NumberFilter(field_name='version', lookup_expr='gte')
    max_version = filters.NumberFilter(field_name='version', lookup_expr='lte')
    
    # Auth filters
    has_basic_auth = filters.BooleanFilter(field_name='basic_auth')
    has_credentials = filters.BooleanFilter(field_name='with_credentials')
    
    # Date filters
    created_after = filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    updated_after = filters.DateTimeFilter(field_name='updated_at', lookup_expr='gte')
    updated_before = filters.DateTimeFilter(field_name='updated_at', lookup_expr='lte')
    synced_after = filters.DateTimeFilter(field_name='synced_at', lookup_expr='gte')
    synced_before = filters.DateTimeFilter(field_name='synced_at', lookup_expr='lte')
    
    class Meta:
        model = GrafanaDatasource
        fields = ['name', 'type', 'is_default', 'is_active', 'server']


# ============================================================================
# FILTRES POUR ALERTES GRAFANA
# ============================================================================

class GrafanaAlertFilter(filters.FilterSet):
    """Filtres pour GrafanaAlert"""
    name = filters.CharFilter(lookup_expr='icontains')
    message = filters.CharFilter(lookup_expr='icontains')
    state = filters.ChoiceFilter(choices=GrafanaAlert.ALERT_STATE_CHOICES)
    severity = filters.ChoiceFilter(choices=GrafanaAlert.SEVERITY_CHOICES)
    
    # Server filters
    server = filters.UUIDFilter(field_name='server__id')
    server_name = filters.CharFilter(field_name='server__name', lookup_expr='icontains')
    
    # Dashboard filters
    dashboard = filters.UUIDFilter(field_name='dashboard__id')
    dashboard_title = filters.CharFilter(field_name='dashboard__title', lookup_expr='icontains')
    
    # Datasource filters
    datasource = filters.UUIDFilter(field_name='datasource__id')
    datasource_name = filters.CharFilter(field_name='datasource__name', lookup_expr='icontains')
    
    # Date filters
    created_after = filters.DateTimeFilter(field_name='created', lookup_expr='gte')
    created_before = filters.DateTimeFilter(field_name='created', lookup_expr='lte')
    updated_after = filters.DateTimeFilter(field_name='updated', lookup_expr='gte')
    updated_before = filters.DateTimeFilter(field_name='updated', lookup_expr='lte')
    state_changed_after = filters.DateTimeFilter(field_name='new_state_date', lookup_expr='gte')
    state_changed_before = filters.DateTimeFilter(field_name='new_state_date', lookup_expr='lte')
    
    # Alert ID
    alert_id = filters.NumberFilter()
    min_alert_id = filters.NumberFilter(field_name='alert_id', lookup_expr='gte')
    max_alert_id = filters.NumberFilter(field_name='alert_id', lookup_expr='lte')
    
    # Firing alerts
    is_firing = filters.BooleanFilter(method='filter_is_firing')
    
    class Meta:
        model = GrafanaAlert
        fields = ['name', 'state', 'severity', 'server', 'dashboard', 'datasource']
    
    def filter_is_firing(self, queryset, name, value):
        if value:
            return queryset.filter(state='firing')
        return queryset.exclude(state='firing')


# ============================================================================
# FILTRES POUR ORGANISATIONS GRAFANA
# ============================================================================

class GrafanaOrganizationFilter(filters.FilterSet):
    """Filtres pour GrafanaOrganization"""
    name = filters.CharFilter(lookup_expr='icontains')
    
    # Server filters
    server = filters.UUIDFilter(field_name='server__id')
    server_name = filters.CharFilter(field_name='server__name', lookup_expr='icontains')
    
    # Org ID
    org_id = filters.NumberFilter()
    min_org_id = filters.NumberFilter(field_name='org_id', lookup_expr='gte')
    max_org_id = filters.NumberFilter(field_name='org_id', lookup_expr='lte')
    
    # Stats filters
    min_users = filters.NumberFilter(method='filter_min_users')
    max_users = filters.NumberFilter(method='filter_max_users')
    min_teams = filters.NumberFilter(method='filter_min_teams')
    max_teams = filters.NumberFilter(method='filter_max_teams')
    
    # Date filters
    created_after = filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    synced_after = filters.DateTimeFilter(field_name='synced_at', lookup_expr='gte')
    synced_before = filters.DateTimeFilter(field_name='synced_at', lookup_expr='lte')
    
    class Meta:
        model = GrafanaOrganization
        fields = ['name', 'server']
    
    def filter_min_users(self, queryset, name, value):
        return queryset.annotate(users_count=Count('users')).filter(users_count__gte=value)
    
    def filter_max_users(self, queryset, name, value):
        return queryset.annotate(users_count=Count('users')).filter(users_count__lte=value)
    
    def filter_min_teams(self, queryset, name, value):
        return queryset.annotate(teams_count=Count('teams')).filter(teams_count__gte=value)
    
    def filter_max_teams(self, queryset, name, value):
        return queryset.annotate(teams_count=Count('teams')).filter(teams_count__lte=value)


# ============================================================================
# FILTRES POUR UTILISATEURS GRAFANA
# ============================================================================

class GrafanaUserFilter(filters.FilterSet):
    """Filtres pour GrafanaUser"""
    email = filters.CharFilter(lookup_expr='icontains')
    name = filters.CharFilter(lookup_expr='icontains')
    login = filters.CharFilter(lookup_expr='icontains')
    role = filters.ChoiceFilter(choices=[('Admin', 'Admin'), ('Editor', 'Editor'), ('Viewer', 'Viewer')])
    is_disabled = filters.BooleanFilter()
    is_active = filters.BooleanFilter()
    
    # Server filters
    server = filters.UUIDFilter(field_name='server__id')
    server_name = filters.CharFilter(field_name='server__name', lookup_expr='icontains')
    
    # Organization filters
    organization = filters.UUIDFilter(field_name='organization__id')
    organization_name = filters.CharFilter(field_name='organization__name', lookup_expr='icontains')
    
    # User ID
    user_id = filters.NumberFilter()
    min_user_id = filters.NumberFilter(field_name='user_id', lookup_expr='gte')
    max_user_id = filters.NumberFilter(field_name='user_id', lookup_expr='lte')
    
    # Date filters
    created_after = filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    last_seen_after = filters.DateTimeFilter(field_name='last_seen_at', lookup_expr='gte')
    last_seen_before = filters.DateTimeFilter(field_name='last_seen_at', lookup_expr='lte')
    synced_after = filters.DateTimeFilter(field_name='synced_at', lookup_expr='gte')
    synced_before = filters.DateTimeFilter(field_name='synced_at', lookup_expr='lte')
    
    class Meta:
        model = GrafanaUser
        fields = ['email', 'role', 'is_active', 'server', 'organization']


# ============================================================================
# FILTRES POUR FOLDERS GRAFANA
# ============================================================================

class GrafanaFolderFilter(filters.FilterSet):
    """Filtres pour GrafanaFolder"""
    title = filters.CharFilter(lookup_expr='icontains')
    folder_uid = filters.CharFilter(lookup_expr='icontains')
    
    # Server filters
    server = filters.UUIDFilter(field_name='server__id')
    server_name = filters.CharFilter(field_name='server__name', lookup_expr='icontains')
    
    # Version filters
    min_version = filters.NumberFilter(field_name='version', lookup_expr='gte')
    max_version = filters.NumberFilter(field_name='version', lookup_expr='lte')
    
    # Date filters
    created_after = filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    synced_after = filters.DateTimeFilter(field_name='synced_at', lookup_expr='gte')
    synced_before = filters.DateTimeFilter(field_name='synced_at', lookup_expr='lte')
    
    class Meta:
        model = GrafanaFolder
        fields = ['title', 'server']


# ============================================================================
# FILTRES POUR PANELS GRAFANA
# ============================================================================

class GrafanaPanelFilter(filters.FilterSet):
    """Filtres pour GrafanaPanel"""
    title = filters.CharFilter(lookup_expr='icontains')
    type = filters.CharFilter(lookup_expr='icontains')
    
    # Dashboard filters
    dashboard = filters.UUIDFilter(field_name='dashboard__id')
    dashboard_title = filters.CharFilter(field_name='dashboard__title', lookup_expr='icontains')
    
    # Panel ID
    panel_id = filters.NumberFilter()
    min_panel_id = filters.NumberFilter(field_name='panel_id', lookup_expr='gte')
    max_panel_id = filters.NumberFilter(field_name='panel_id', lookup_expr='lte')
    
    # Date filters
    created_after = filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    
    class Meta:
        model = GrafanaPanel
        fields = ['title', 'type', 'dashboard']


# ============================================================================
# FILTRES POUR SNAPSHOTS GRAFANA
# ============================================================================

class GrafanaSnapshotFilter(filters.FilterSet):
    """Filtres pour GrafanaSnapshot"""
    name = filters.CharFilter(lookup_expr='icontains')
    snapshot_key = filters.CharFilter(lookup_expr='icontains')
    created_by = filters.CharFilter(lookup_expr='icontains')
    
    # Server filters
    server = filters.UUIDFilter(field_name='server__id')
    server_name = filters.CharFilter(field_name='server__name', lookup_expr='icontains')
    
    # Dashboard filters
    dashboard = filters.UUIDFilter(field_name='dashboard__id')
    dashboard_title = filters.CharFilter(field_name='dashboard__title', lookup_expr='icontains')
    
    # Date filters
    created_after = filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    expires_after = filters.DateTimeFilter(field_name='expires_at', lookup_expr='gte')
    expires_before = filters.DateTimeFilter(field_name='expires_at', lookup_expr='lte')
    
    # Expired
    is_expired = filters.BooleanFilter(method='filter_is_expired')
    
    class Meta:
        model = GrafanaSnapshot
        fields = ['name', 'server', 'dashboard', 'created_by']
    
    def filter_is_expired(self, queryset, name, value):
        from django.utils import timezone
        now = timezone.now()
        if value:
            return queryset.filter(expires_at__lt=now)
        return queryset.filter(Q(expires_at__isnull=True) | Q(expires_at__gte=now))


# ============================================================================
# FILTRES POUR TEAMS GRAFANA
# ============================================================================

class GrafanaTeamFilter(filters.FilterSet):
    """Filtres pour GrafanaTeam"""
    name = filters.CharFilter(lookup_expr='icontains')
    email = filters.CharFilter(lookup_expr='icontains')
    
    # Server filters
    server = filters.UUIDFilter(field_name='server__id')
    server_name = filters.CharFilter(field_name='server__name', lookup_expr='icontains')
    
    # Organization filters
    organization = filters.UUIDFilter(field_name='organization__id')
    organization_name = filters.CharFilter(field_name='organization__name', lookup_expr='icontains')
    
    # Team ID
    team_id = filters.NumberFilter()
    min_team_id = filters.NumberFilter(field_name='team_id', lookup_expr='gte')
    max_team_id = filters.NumberFilter(field_name='team_id', lookup_expr='lte')
    
    # Member count filters
    min_members = filters.NumberFilter(field_name='member_count', lookup_expr='gte')
    max_members = filters.NumberFilter(field_name='member_count', lookup_expr='lte')
    
    # Permission filters
    min_permission = filters.NumberFilter(field_name='permission', lookup_expr='gte')
    max_permission = filters.NumberFilter(field_name='permission', lookup_expr='lte')
    
    # Date filters
    created_after = filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    synced_after = filters.DateTimeFilter(field_name='synced_at', lookup_expr='gte')
    synced_before = filters.DateTimeFilter(field_name='synced_at', lookup_expr='lte')
    
    class Meta:
        model = GrafanaTeam
        fields = ['name', 'server', 'organization']