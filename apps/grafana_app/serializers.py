"""
Grafana App Serializers - API serializers professionnels
"""
from rest_framework import serializers
from django.utils import timezone
from .models import (
    GrafanaServer, GrafanaDashboard, GrafanaDatasource, GrafanaAlert,
    GrafanaOrganization, GrafanaUser, GrafanaFolder, GrafanaPanel,
    GrafanaSnapshot, GrafanaTeam
)


# ============================================================================
# SERVEURS GRAFANA
# ============================================================================

class GrafanaServerSerializer(serializers.ModelSerializer):
    """Serializer de base pour les serveurs Grafana"""
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True, allow_null=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    dashboards_count = serializers.IntegerField(source='dashboards.count', read_only=True)
    datasources_count = serializers.IntegerField(source='datasources.count', read_only=True)
    alerts_count = serializers.IntegerField(source='alerts.count', read_only=True)
    
    class Meta:
        model = GrafanaServer
        fields = [
            'id', 'name', 'description', 'url', 'api_key', 'username', 'password',
            'timeout', 'status', 'status_display', 'version', 'last_sync_at',
            'dashboards_count', 'datasources_count', 'alerts_count',
            'created_by', 'created_by_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by',
                           'version', 'last_sync_at', 'dashboards_count',
                           'datasources_count', 'alerts_count']
        extra_kwargs = {
            'api_key': {'write_only': True},
            'password': {'write_only': True},
        }


class GrafanaServerDetailSerializer(GrafanaServerSerializer):
    """Serializer détaillé pour les serveurs Grafana"""
    dashboards = serializers.SerializerMethodField()
    datasources = serializers.SerializerMethodField()
    alerts = serializers.SerializerMethodField()
    organizations = serializers.SerializerMethodField()
    users = serializers.SerializerMethodField()
    
    class Meta(GrafanaServerSerializer.Meta):
        fields = GrafanaServerSerializer.Meta.fields + [
            'dashboards', 'datasources', 'alerts', 'organizations', 'users'
        ]
    
    def get_dashboards(self, obj):
        dashboards = obj.dashboards.all()[:10]
        return [{
            'id': str(d.id),
            'title': d.title,
            'dashboard_uid': d.dashboard_uid,
            'version': d.version,
            'is_active': d.is_active
        } for d in dashboards]
    
    def get_datasources(self, obj):
        datasources = obj.datasources.all()[:10]
        return [{
            'id': str(d.id),
            'name': d.name,
            'type': d.get_type_display(),
            'is_default': d.is_default,
            'is_active': d.is_active
        } for d in datasources]
    
    def get_alerts(self, obj):
        alerts = obj.alerts.filter(state='firing')[:10]
        return [{
            'id': str(a.id),
            'name': a.name,
            'state': a.get_state_display(),
            'severity': a.get_severity_display(),
            'new_state_date': a.new_state_date
        } for a in alerts]
    
    def get_organizations(self, obj):
        orgs = obj.organizations.all()
        return [{
            'id': str(o.id),
            'name': o.name,
            'org_id': o.org_id
        } for o in orgs]
    
    def get_users(self, obj):
        users = obj.users.all()[:10]
        return [{
            'id': str(u.id),
            'email': u.email,
            'name': u.name,
            'role': u.role,
            'is_active': u.is_active
        } for u in users]


# ============================================================================
# DASHBOARDS GRAFANA
# ============================================================================

class GrafanaDashboardSerializer(serializers.ModelSerializer):
    """Serializer pour les dashboards Grafana"""
    server_name = serializers.CharField(source='server.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True, allow_null=True)
    folder_title = serializers.CharField(read_only=True)
    panels_count = serializers.IntegerField(source='panels.count', read_only=True)
    
    class Meta:
        model = GrafanaDashboard
        fields = [
            'id', 'server', 'server_name', 'dashboard_uid', 'title', 'description',
            'dashboard_json', 'version', 'url', 'slug', 'tags',
            'folder_title', 'panels_count', 'synced_at', 'is_active',
            'created_by', 'created_by_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'synced_at',
                           'version', 'folder_title', 'panels_count']


class GrafanaDashboardDetailSerializer(GrafanaDashboardSerializer):
    """Serializer détaillé pour les dashboards"""
    panels = serializers.SerializerMethodField()
    alerts = serializers.SerializerMethodField()
    
    class Meta(GrafanaDashboardSerializer.Meta):
        fields = GrafanaDashboardSerializer.Meta.fields + ['panels', 'alerts']
    
    def get_panels(self, obj):
        panels = obj.panels.all().order_by('panel_id')
        return [{
            'id': str(p.id),
            'panel_id': p.panel_id,
            'title': p.title,
            'type': p.type,
            'grid_pos': p.grid_pos
        } for p in panels]
    
    def get_alerts(self, obj):
        alerts = obj.alerts.all()
        return [{
            'id': str(a.id),
            'name': a.name,
            'state': a.get_state_display(),
            'severity': a.get_severity_display()
        } for a in alerts]


# ============================================================================
# DATASOURCES GRAFANA
# ============================================================================

class GrafanaDatasourceSerializer(serializers.ModelSerializer):
    """Serializer pour les sources de données Grafana"""
    server_name = serializers.CharField(source='server.name', read_only=True)
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    
    class Meta:
        model = GrafanaDatasource
        fields = [
            'id', 'server', 'server_name', 'datasource_uid', 'name', 'type',
            'type_display', 'url', 'access', 'is_default', 'basic_auth',
            'basic_auth_user', 'basic_auth_password', 'with_credentials',
            'json_data', 'secure_json_data', 'version', 'read_only',
            'synced_at', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'synced_at', 'version']
        extra_kwargs = {
            'basic_auth_password': {'write_only': True},
            'secure_json_data': {'write_only': True},
        }


# ============================================================================
# ALERTES GRAFANA
# ============================================================================

class GrafanaAlertSerializer(serializers.ModelSerializer):
    """Serializer pour les alertes Grafana"""
    server_name = serializers.CharField(source='server.name', read_only=True)
    dashboard_title = serializers.CharField(source='dashboard.title', read_only=True, allow_null=True)
    datasource_name = serializers.CharField(source='datasource.name', read_only=True, allow_null=True)
    state_display = serializers.CharField(source='get_state_display', read_only=True)
    severity_display = serializers.CharField(source='get_severity_display', read_only=True)
    
    class Meta:
        model = GrafanaAlert
        fields = [
            'id', 'server', 'server_name', 'dashboard', 'dashboard_title',
            'datasource', 'datasource_name', 'alert_id', 'name', 'message',
            'state', 'state_display', 'severity', 'severity_display',
            'created', 'updated', 'new_state_date', 'eval_data',
            'execution_error', 'url', 'synced_at', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'synced_at']


# ============================================================================
# ORGANISATIONS GRAFANA
# ============================================================================

class GrafanaOrganizationSerializer(serializers.ModelSerializer):
    """Serializer pour les organisations Grafana"""
    server_name = serializers.CharField(source='server.name', read_only=True)
    users_count = serializers.SerializerMethodField()
    teams_count = serializers.SerializerMethodField()
    
    class Meta:
        model = GrafanaOrganization
        fields = [
            'id', 'server', 'server_name', 'org_id', 'name', 'address',
            'users_count', 'teams_count', 'synced_at', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'synced_at']
    
    def get_users_count(self, obj):
        return obj.users.count()
    
    def get_teams_count(self, obj):
        return obj.teams.count()


# ============================================================================
# UTILISATEURS GRAFANA
# ============================================================================

class GrafanaUserSerializer(serializers.ModelSerializer):
    """Serializer pour les utilisateurs Grafana"""
    server_name = serializers.CharField(source='server.name', read_only=True)
    organization_name = serializers.CharField(source='organization.name', read_only=True, allow_null=True)
    
    class Meta:
        model = GrafanaUser
        fields = [
            'id', 'server', 'server_name', 'organization', 'organization_name',
            'user_id', 'email', 'name', 'login', 'role', 'is_disabled',
            'is_active', 'avatar_url', 'last_seen_at', 'synced_at',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'synced_at', 'last_seen_at']


# ============================================================================
# FOLDERS GRAFANA
# ============================================================================

class GrafanaFolderSerializer(serializers.ModelSerializer):
    """Serializer pour les dossiers Grafana"""
    server_name = serializers.CharField(source='server.name', read_only=True)
    dashboards_count = serializers.SerializerMethodField()
    
    class Meta:
        model = GrafanaFolder
        fields = [
            'id', 'server', 'server_name', 'folder_uid', 'title', 'url',
            'version', 'dashboards_count', 'synced_at', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'synced_at', 'version']
    
    def get_dashboards_count(self, obj):
        # Cette méthode nécessiterait une relation dashboard->folder
        # À implémenter si nécessaire
        return 0


# ============================================================================
# PANELS GRAFANA
# ============================================================================

class GrafanaPanelSerializer(serializers.ModelSerializer):
    """Serializer pour les panels Grafana"""
    dashboard_title = serializers.CharField(source='dashboard.title', read_only=True)
    
    class Meta:
        model = GrafanaPanel
        fields = [
            'id', 'dashboard', 'dashboard_title', 'panel_id', 'title', 'type',
            'panel_json', 'grid_pos', 'targets', 'description',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


# ============================================================================
# SNAPSHOTS GRAFANA
# ============================================================================

class GrafanaSnapshotSerializer(serializers.ModelSerializer):
    """Serializer pour les snapshots Grafana"""
    server_name = serializers.CharField(source='server.name', read_only=True)
    dashboard_title = serializers.CharField(source='dashboard.title', read_only=True, allow_null=True)
    
    class Meta:
        model = GrafanaSnapshot
        fields = [
            'id', 'server', 'server_name', 'dashboard', 'dashboard_title',
            'snapshot_key', 'snapshot_url', 'snapshot_json', 'name',
            'expires_at', 'created_by', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'expires_at']


# ============================================================================
# TEAMS GRAFANA
# ============================================================================

class GrafanaTeamSerializer(serializers.ModelSerializer):
    """Serializer pour les teams Grafana"""
    server_name = serializers.CharField(source='server.name', read_only=True)
    organization_name = serializers.CharField(source='organization.name', read_only=True, allow_null=True)
    
    class Meta:
        model = GrafanaTeam
        fields = [
            'id', 'server', 'server_name', 'organization', 'organization_name',
            'team_id', 'name', 'email', 'member_count', 'permission',
            'synced_at', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'synced_at', 'member_count']


# ============================================================================
# REQUESTS
# ============================================================================

class GrafanaDashboardImportSerializer(serializers.Serializer):
    """Serializer pour importer un dashboard"""
    dashboard_json = serializers.JSONField(required=True)
    overwrite = serializers.BooleanField(default=False)
    folder_id = serializers.IntegerField(required=False, allow_null=True)
    message = serializers.CharField(required=False, allow_blank=True)


class GrafanaDatasourceCreateSerializer(serializers.Serializer):
    """Serializer pour créer une datasource"""
    name = serializers.CharField(required=True)
    type = serializers.ChoiceField(choices=GrafanaDatasource.DATASOURCE_TYPE_CHOICES)
    url = serializers.URLField(required=True)
    access = serializers.ChoiceField(choices=[('direct', 'Direct'), ('proxy', 'Proxy')], default='proxy')
    is_default = serializers.BooleanField(default=False)
    basic_auth = serializers.BooleanField(default=False)
    basic_auth_user = serializers.CharField(required=False, allow_blank=True)
    basic_auth_password = serializers.CharField(required=False, allow_blank=True)
    json_data = serializers.JSONField(default=dict)
    secure_json_data = serializers.JSONField(default=dict)


# ============================================================================
# DASHBOARD
# ============================================================================

class GrafanaDashboardStatsSerializer(serializers.Serializer):
    """Serializer pour les statistiques du dashboard"""
    total_servers = serializers.IntegerField()
    active_servers = serializers.IntegerField()
    total_dashboards = serializers.IntegerField()
    total_datasources = serializers.IntegerField()
    total_alerts = serializers.IntegerField()
    firing_alerts = serializers.IntegerField()
    total_users = serializers.IntegerField()
    total_organizations = serializers.IntegerField()


class GrafanaRecentDashboardSerializer(serializers.Serializer):
    """Serializer pour les dashboards récents"""
    id = serializers.UUIDField()
    title = serializers.CharField()
    server_name = serializers.CharField()
    version = serializers.IntegerField()
    updated_at = serializers.DateTimeField()
    is_active = serializers.BooleanField()


class GrafanaAlertSummarySerializer(serializers.Serializer):
    """Serializer pour le résumé des alertes"""
    id = serializers.UUIDField()
    name = serializers.CharField()
    state = serializers.CharField()
    severity = serializers.CharField()
    dashboard = serializers.CharField(allow_null=True)
    new_state_date = serializers.DateTimeField()


class GrafanaDashboardSummarySerializer(serializers.Serializer):
    """Serializer pour le dashboard Grafana"""
    statistics = GrafanaDashboardStatsSerializer()
    recent_dashboards = GrafanaRecentDashboardSerializer(many=True)
    recent_alerts = GrafanaAlertSummarySerializer(many=True)
    datasources_by_type = serializers.ListField(child=serializers.DictField())
    alerts_by_state = serializers.ListField(child=serializers.DictField())