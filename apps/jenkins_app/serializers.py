"""
Jenkins App Serializers - API serializers professionnels
"""
from rest_framework import serializers
from django.utils import timezone
from .models import (
    JenkinsServer, JenkinsJob, JenkinsBuild, JenkinsNode,
    JenkinsPlugin, JenkinsCredential, JenkinsView, JenkinsPipeline
)


# ============================================================================
# SERVEURS JENKINS
# ============================================================================

class JenkinsServerSerializer(serializers.ModelSerializer):
    """Serializer de base pour les serveurs Jenkins"""
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True, allow_null=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    jobs_count = serializers.IntegerField(source='jobs.count', read_only=True)
    nodes_count = serializers.IntegerField(source='nodes.count', read_only=True)
    
    class Meta:
        model = JenkinsServer
        fields = [
            'id', 'name', 'description', 'url', 'username', 'password',
            'timeout', 'max_concurrent_builds', 'status', 'status_display',
            'version', 'last_sync_at', 'jobs_count', 'nodes_count',
            'created_by', 'created_by_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by',
                           'version', 'last_sync_at', 'jobs_count', 'nodes_count']
        extra_kwargs = {
            'password': {'write_only': True},
        }
    
    def validate_url(self, value):
        """Valide l'URL"""
        if not value.startswith(('http://', 'https://')):
            raise serializers.ValidationError("URL must start with http:// or https://")
        return value.rstrip('/')


class JenkinsServerDetailSerializer(JenkinsServerSerializer):
    """Serializer détaillé pour les serveurs Jenkins"""
    jobs = serializers.SerializerMethodField()
    nodes = serializers.SerializerMethodField()
    plugins = serializers.SerializerMethodField()
    views = serializers.SerializerMethodField()
    
    class Meta(JenkinsServerSerializer.Meta):
        fields = JenkinsServerSerializer.Meta.fields + [
            'jobs', 'nodes', 'plugins', 'views'
        ]
    
    def get_jobs(self, obj):
        jobs = obj.jobs.all()[:10]
        return [{
            'id': str(j.id),
            'name': j.name,
            'job_type': j.job_type,
            'color': j.color,
            'last_build_status': j.last_build_status,
            'last_build_at': j.last_build_at
        } for j in jobs]
    
    def get_nodes(self, obj):
        nodes = obj.nodes.all()
        return [{
            'id': str(n.id),
            'name': n.name,
            'node_type': n.node_type,
            'status': n.status,
            'num_executors': n.num_executors
        } for n in nodes]
    
    def get_plugins(self, obj):
        plugins = obj.plugins.all()[:20]
        return [{
            'id': str(p.id),
            'name': p.name,
            'version': p.version,
            'enabled': p.enabled,
            'has_update': p.has_update
        } for p in plugins]
    
    def get_views(self, obj):
        views = obj.views.all()
        return [{
            'id': str(v.id),
            'name': v.name,
            'view_type': v.view_type,
            'jobs_count': len(v.jobs) if v.jobs else 0
        } for v in views]


# ============================================================================
# JOBS JENKINS
# ============================================================================

class JenkinsJobSerializer(serializers.ModelSerializer):
    """Serializer pour les jobs Jenkins"""
    server_name = serializers.CharField(source='server.name', read_only=True)
    status_badge = serializers.CharField(read_only=True)
    last_build_status_display = serializers.CharField(source='get_last_build_status_display', read_only=True)
    
    class Meta:
        model = JenkinsJob
        fields = [
            'id', 'server', 'server_name', 'job_id', 'name', 'description',
            'job_type', 'url', 'config_xml', 'parameters', 'color', 'health_report',
            'last_build_number', 'last_build_status', 'last_build_status_display',
            'last_build_at', 'build_count', 'status_badge', 'synced_at', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'synced_at',
                           'last_build_number', 'last_build_status', 'last_build_at',
                           'build_count', 'color', 'health_report']


class JenkinsJobDetailSerializer(JenkinsJobSerializer):
    """Serializer détaillé pour les jobs Jenkins"""
    builds = serializers.SerializerMethodField()
    
    class Meta(JenkinsJobSerializer.Meta):
        fields = JenkinsJobSerializer.Meta.fields + ['builds']
    
    def get_builds(self, obj):
        builds = obj.builds.order_by('-build_number')[:10]
        return [{
            'id': str(b.id),
            'build_number': b.build_number,
            'status': b.status,
            'result': b.result,
            'started_at': b.started_at,
            'duration': b.duration,
            'built_by': b.built_by
        } for b in builds]


# ============================================================================
# BUILDS JENKINS
# ============================================================================

class JenkinsBuildSerializer(serializers.ModelSerializer):
    """Serializer pour les builds Jenkins"""
    job_name = serializers.CharField(source='job.name', read_only=True)
    server_name = serializers.CharField(source='job.server.name', read_only=True)
    status_badge = serializers.CharField(read_only=True)
    duration_display = serializers.SerializerMethodField()
    
    class Meta:
        model = JenkinsBuild
        fields = [
            'id', 'job', 'job_name', 'server_name', 'build_number', 'status',
            'status_badge', 'started_at', 'completed_at', 'duration', 'duration_display',
            'estimated_duration', 'result', 'url', 'console_output', 'parameters',
            'causes', 'built_by', 'triggered_by', 'test_results', 'artifacts', 'metrics',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'duration',
                           'console_output', 'test_results', 'artifacts', 'metrics']
    
    def get_duration_display(self, obj):
        if obj.duration:
            if obj.duration < 60:
                return f"{obj.duration:.1f}s"
            elif obj.duration < 3600:
                return f"{obj.duration/60:.1f}m"
            else:
                return f"{obj.duration/3600:.1f}h"
        return None


class JenkinsBuildDetailSerializer(JenkinsBuildSerializer):
    """Serializer détaillé pour les builds"""
    
    class Meta(JenkinsBuildSerializer.Meta):
        fields = JenkinsBuildSerializer.Meta.fields


# ============================================================================
# NŒUDS JENKINS
# ============================================================================

class JenkinsNodeSerializer(serializers.ModelSerializer):
    """Serializer pour les nœuds Jenkins"""
    server_name = serializers.CharField(source='server.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = JenkinsNode
        fields = [
            'id', 'server', 'server_name', 'node_id', 'name', 'node_type',
            'url', 'description', 'status', 'status_display', 'offline_reason',
            'num_executors', 'total_memory', 'free_memory', 'total_disk',
            'free_disk', 'cpu_cores', 'load_average', 'labels',
            'synced_at', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'synced_at']


# ============================================================================
# PLUGINS JENKINS
# ============================================================================

class JenkinsPluginSerializer(serializers.ModelSerializer):
    """Serializer pour les plugins Jenkins"""
    server_name = serializers.CharField(source='server.name', read_only=True)
    
    class Meta:
        model = JenkinsPlugin
        fields = [
            'id', 'server', 'server_name', 'plugin_id', 'name', 'version',
            'title', 'description', 'url', 'enabled', 'has_update',
            'compatible_version', 'dependencies', 'installed_at', 'updated_at',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'installed_at', 'updated_at']


# ============================================================================
# CREDENTIALS JENKINS
# ============================================================================

class JenkinsCredentialSerializer(serializers.ModelSerializer):
    """Serializer pour les credentials Jenkins"""
    server_name = serializers.CharField(source='server.name', read_only=True)
    credential_type_display = serializers.CharField(source='get_credential_type_display', read_only=True)
    
    class Meta:
        model = JenkinsCredential
        fields = [
            'id', 'server', 'server_name', 'credential_id', 'name',
            'credential_type', 'credential_type_display', 'description',
            'username', 'password', 'private_key', 'passphrase', 'secret',
            'scope', 'synced_at', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'synced_at']
        extra_kwargs = {
            'password': {'write_only': True},
            'private_key': {'write_only': True},
            'passphrase': {'write_only': True},
            'secret': {'write_only': True},
        }


# ============================================================================
# VUES JENKINS
# ============================================================================

class JenkinsViewSerializer(serializers.ModelSerializer):
    """Serializer pour les vues Jenkins"""
    server_name = serializers.CharField(source='server.name', read_only=True)
    
    class Meta:
        model = JenkinsView
        fields = [
            'id', 'server', 'server_name', 'view_id', 'name', 'description',
            'url', 'view_type', 'jobs', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


# ============================================================================
# PIPELINES JENKINS
# ============================================================================

class JenkinsPipelineSerializer(serializers.ModelSerializer):
    """Serializer pour les pipelines Jenkins"""
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True, allow_null=True)
    jobs_count = serializers.IntegerField(source='jobs.count', read_only=True)
    
    class Meta:
        model = JenkinsPipeline
        fields = [
            'id', 'name', 'description', 'jobs', 'jobs_count',
            'parameters', 'environment', 'pipeline_script',
            'created_by', 'created_by_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by', 'jobs_count']


class JenkinsPipelineDetailSerializer(JenkinsPipelineSerializer):
    """Serializer détaillé pour les pipelines"""
    jobs_list = serializers.SerializerMethodField()
    
    class Meta(JenkinsPipelineSerializer.Meta):
        fields = JenkinsPipelineSerializer.Meta.fields + ['jobs_list']
    
    def get_jobs_list(self, obj):
        return [{
            'id': str(j.id),
            'name': j.name,
            'job_type': j.job_type,
            'url': j.url
        } for j in obj.jobs.all()]


# ============================================================================
# REQUESTS
# ============================================================================

class JenkinsBuildTriggerSerializer(serializers.Serializer):
    """Serializer pour déclencher un build"""
    parameters = serializers.JSONField(required=False, default=dict)
    wait = serializers.BooleanField(default=False, help_text="Wait for build completion")
    timeout = serializers.IntegerField(default=300, help_text="Timeout in seconds")


class JenkinsJobSyncSerializer(serializers.Serializer):
    """Serializer pour synchroniser un job"""
    sync_builds = serializers.BooleanField(default=True, help_text="Sync build history")
    sync_config = serializers.BooleanField(default=True, help_text="Sync job configuration")
    limit = serializers.IntegerField(default=50, help_text="Number of builds to sync")


# ============================================================================
# DASHBOARD
# ============================================================================

class JenkinsDashboardStatsSerializer(serializers.Serializer):
    """Serializer pour les statistiques du dashboard"""
    total_servers = serializers.IntegerField()
    active_servers = serializers.IntegerField()
    total_jobs = serializers.IntegerField()
    total_pipelines = serializers.IntegerField()
    builds_24h = serializers.IntegerField()
    successful_builds_24h = serializers.IntegerField()
    failed_builds_24h = serializers.IntegerField()
    success_rate_24h = serializers.FloatField()
    avg_duration_24h = serializers.FloatField()
    queue_size = serializers.IntegerField()
    idle_executors = serializers.IntegerField()


class JenkinsRecentBuildSerializer(serializers.Serializer):
    """Serializer pour les builds récents"""
    id = serializers.UUIDField()
    job_name = serializers.CharField()
    build_number = serializers.IntegerField()
    status = serializers.CharField()
    result = serializers.CharField()
    started_at = serializers.DateTimeField()
    duration = serializers.FloatField(allow_null=True)
    built_by = serializers.CharField(allow_null=True)


class JenkinsTopJobSerializer(serializers.Serializer):
    """Serializer pour les jobs les plus actifs"""
    id = serializers.UUIDField()
    name = serializers.CharField()
    build_count = serializers.IntegerField()
    last_build_status = serializers.CharField()
    success_rate = serializers.FloatField()


class JenkinsDashboardSerializer(serializers.Serializer):
    """Serializer pour le dashboard Jenkins"""
    statistics = JenkinsDashboardStatsSerializer()
    recent_builds = JenkinsRecentBuildSerializer(many=True)
    top_jobs = JenkinsTopJobSerializer(many=True)
    queue = serializers.ListField(child=serializers.DictField())
    nodes_status = serializers.DictField()