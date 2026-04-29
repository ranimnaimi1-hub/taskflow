"""
Jenkins App Filters - Filtres personnalisés pour l'API
"""
import django_filters
from django_filters import rest_framework as filters
from django.db import models
from django.db.models import Q, Count, Avg
from .models import (
    JenkinsServer, JenkinsJob, JenkinsBuild, JenkinsNode,
    JenkinsPlugin, JenkinsCredential, JenkinsView, JenkinsPipeline
)


# ============================================================================
# FILTRES POUR SERVEURS JENKINS
# ============================================================================

class JenkinsServerFilter(filters.FilterSet):
    """Filtres pour JenkinsServer"""
    name = filters.CharFilter(lookup_expr='icontains')
    description = filters.CharFilter(lookup_expr='icontains')
    url = filters.CharFilter(lookup_expr='icontains')
    status = filters.ChoiceFilter(choices=JenkinsServer.STATUS_CHOICES)
    
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
    min_jobs = filters.NumberFilter(method='filter_min_jobs')
    max_jobs = filters.NumberFilter(method='filter_max_jobs')
    has_version = filters.BooleanFilter(field_name='version', lookup_expr='isnull', exclude=True)
    is_active = filters.BooleanFilter(field_name='status', method='filter_is_active')
    
    class Meta:
        model = JenkinsServer
        fields = ['name', 'status', 'created_by']
    
    def filter_min_jobs(self, queryset, name, value):
        """Filtre les serveurs avec un nombre minimum de jobs"""
        return queryset.annotate(jobs_count=Count('jobs')).filter(jobs_count__gte=value)
    
    def filter_max_jobs(self, queryset, name, value):
        """Filtre les serveurs avec un nombre maximum de jobs"""
        return queryset.annotate(jobs_count=Count('jobs')).filter(jobs_count__lte=value)
    
    def filter_is_active(self, queryset, name, value):
        """Filtre les serveurs actifs/inactifs"""
        if value:
            return queryset.filter(status='active')
        return queryset.exclude(status='active')


# ============================================================================
# FILTRES POUR JOBS JENKINS
# ============================================================================

class JenkinsJobFilter(filters.FilterSet):
    """Filtres pour JenkinsJob"""
    name = filters.CharFilter(lookup_expr='icontains')
    description = filters.CharFilter(lookup_expr='icontains')
    job_type = filters.ChoiceFilter(choices=JenkinsJob.JOB_TYPE_CHOICES)
    color = filters.CharFilter(lookup_expr='icontains')
    is_active = filters.BooleanFilter()
    
    # Server filters
    server = filters.UUIDFilter(field_name='server__id')
    server_name = filters.CharFilter(field_name='server__name', lookup_expr='icontains')
    
    # Build stats filters
    min_build_count = filters.NumberFilter(field_name='build_count', lookup_expr='gte')
    max_build_count = filters.NumberFilter(field_name='build_count', lookup_expr='lte')
    last_build_status = filters.CharFilter(field_name='last_build_status', lookup_expr='icontains')
    last_build_after = filters.DateTimeFilter(field_name='last_build_at', lookup_expr='gte')
    last_build_before = filters.DateTimeFilter(field_name='last_build_at', lookup_expr='lte')
    
    # Date filters
    created_after = filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    updated_after = filters.DateTimeFilter(field_name='updated_at', lookup_expr='gte')
    updated_before = filters.DateTimeFilter(field_name='updated_at', lookup_expr='lte')
    synced_after = filters.DateTimeFilter(field_name='synced_at', lookup_expr='gte')
    synced_before = filters.DateTimeFilter(field_name='synced_at', lookup_expr='lte')
    
    # Parameter filters
    has_parameters = filters.BooleanFilter(method='filter_has_parameters')
    parameter_name = filters.CharFilter(method='filter_parameter_name')
    
    # Health filters
    health_score_min = filters.NumberFilter(method='filter_health_score_min')
    health_score_max = filters.NumberFilter(method='filter_health_score_max')
    
    class Meta:
        model = JenkinsJob
        fields = ['name', 'job_type', 'is_active', 'server', 'last_build_status']
    
    def filter_has_parameters(self, queryset, name, value):
        """Filtre les jobs qui ont des paramètres"""
        if value:
            return queryset.exclude(parameters=[])
        return queryset.filter(parameters=[])
    
    def filter_parameter_name(self, queryset, name, value):
        """Filtre les jobs qui ont un paramètre spécifique"""
        return queryset.filter(parameters__contains=[{'name': value}])
    
    def filter_health_score_min(self, queryset, name, value):
        """Filtre les jobs avec un score de santé minimum"""
        result_ids = []
        for job in queryset:
            health = job.health_report or {}
            score = health.get('score', 0)
            if score >= value:
                result_ids.append(job.id)
        return queryset.filter(id__in=result_ids)
    
    def filter_health_score_max(self, queryset, name, value):
        """Filtre les jobs avec un score de santé maximum"""
        result_ids = []
        for job in queryset:
            health = job.health_report or {}
            score = health.get('score', 0)
            if score <= value:
                result_ids.append(job.id)
        return queryset.filter(id__in=result_ids)


# ============================================================================
# FILTRES POUR BUILDS JENKINS
# ============================================================================

class JenkinsBuildFilter(filters.FilterSet):
    """Filtres pour JenkinsBuild"""
    status = filters.ChoiceFilter(choices=JenkinsBuild.BUILD_STATUS_CHOICES)
    result = filters.CharFilter(lookup_expr='icontains')
    build_number = filters.NumberFilter()
    
    # Job filters
    job = filters.UUIDFilter(field_name='job__id')
    job_name = filters.CharFilter(field_name='job__name', lookup_expr='icontains')
    server = filters.UUIDFilter(field_name='job__server__id')
    server_name = filters.CharFilter(field_name='job__server__name', lookup_expr='icontains')
    
    # Range filters for build number
    min_build_number = filters.NumberFilter(field_name='build_number', lookup_expr='gte')
    max_build_number = filters.NumberFilter(field_name='build_number', lookup_expr='lte')
    
    # Date filters
    started_after = filters.DateTimeFilter(field_name='started_at', lookup_expr='gte')
    started_before = filters.DateTimeFilter(field_name='started_at', lookup_expr='lte')
    completed_after = filters.DateTimeFilter(field_name='completed_at', lookup_expr='gte')
    completed_before = filters.DateTimeFilter(field_name='completed_at', lookup_expr='lte')
    created_after = filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    
    # Duration filters
    min_duration = filters.NumberFilter(field_name='duration', lookup_expr='gte')
    max_duration = filters.NumberFilter(field_name='duration', lookup_expr='lte')
    
    # User filters
    built_by = filters.CharFilter(lookup_expr='icontains')
    triggered_by = filters.UUIDFilter(field_name='triggered_by__id')
    triggered_by_name = filters.CharFilter(field_name='triggered_by__email', lookup_expr='icontains')
    
    # Success/failure
    is_success = filters.BooleanFilter(method='filter_is_success')
    is_failure = filters.BooleanFilter(method='filter_is_failure')
    
    # Has artifacts
    has_artifacts = filters.BooleanFilter(method='filter_has_artifacts')
    has_tests = filters.BooleanFilter(method='filter_has_tests')
    
    class Meta:
        model = JenkinsBuild
        fields = ['status', 'result', 'job', 'built_by']
    
    def filter_is_success(self, queryset, name, value):
        """Filtre les builds réussis"""
        if value:
            return queryset.filter(status='completed', result='SUCCESS')
        return queryset.exclude(status='completed', result='SUCCESS')
    
    def filter_is_failure(self, queryset, name, value):
        """Filtre les builds échoués"""
        if value:
            return queryset.filter(status='failed')
        return queryset.exclude(status='failed')
    
    def filter_has_artifacts(self, queryset, name, value):
        """Filtre les builds qui ont des artifacts"""
        if value:
            return queryset.exclude(artifacts=[])
        return queryset.filter(artifacts=[])
    
    def filter_has_tests(self, queryset, name, value):
        """Filtre les builds qui ont des tests"""
        if value:
            return queryset.exclude(test_results={})
        return queryset.filter(test_results={})


# ============================================================================
# FILTRES POUR NŒUDS JENKINS
# ============================================================================

class JenkinsNodeFilter(filters.FilterSet):
    """Filtres pour JenkinsNode"""
    name = filters.CharFilter(lookup_expr='icontains')
    node_type = filters.ChoiceFilter(choices=JenkinsNode.NODE_TYPE_CHOICES)
    status = filters.ChoiceFilter(choices=JenkinsNode.STATUS_CHOICES)
    
    # Server filters
    server = filters.UUIDFilter(field_name='server__id')
    server_name = filters.CharFilter(field_name='server__name', lookup_expr='icontains')
    
    # Capacity filters
    min_executors = filters.NumberFilter(field_name='num_executors', lookup_expr='gte')
    max_executors = filters.NumberFilter(field_name='num_executors', lookup_expr='lte')
    min_memory = filters.NumberFilter(field_name='total_memory', lookup_expr='gte')
    max_memory = filters.NumberFilter(field_name='total_memory', lookup_expr='lte')
    min_disk = filters.NumberFilter(field_name='total_disk', lookup_expr='gte')
    max_disk = filters.NumberFilter(field_name='total_disk', lookup_expr='lte')
    min_cores = filters.NumberFilter(field_name='cpu_cores', lookup_expr='gte')
    max_cores = filters.NumberFilter(field_name='cpu_cores', lookup_expr='lte')
    
    # Load filters
    min_load = filters.NumberFilter(field_name='load_average', lookup_expr='gte')
    max_load = filters.NumberFilter(field_name='load_average', lookup_expr='lte')
    
    # Label filters
    has_label = filters.CharFilter(method='filter_has_label')
    
    # Date filters
    synced_after = filters.DateTimeFilter(field_name='synced_at', lookup_expr='gte')
    synced_before = filters.DateTimeFilter(field_name='synced_at', lookup_expr='lte')
    
    class Meta:
        model = JenkinsNode
        fields = ['name', 'node_type', 'status', 'server']
    
    def filter_has_label(self, queryset, name, value):
        """Filtre les nœuds qui ont un label spécifique"""
        return queryset.filter(labels__contains=[value])


# ============================================================================
# FILTRES POUR PLUGINS JENKINS
# ============================================================================

class JenkinsPluginFilter(filters.FilterSet):
    """Filtres pour JenkinsPlugin"""
    name = filters.CharFilter(lookup_expr='icontains')
    title = filters.CharFilter(lookup_expr='icontains')
    version = filters.CharFilter(lookup_expr='icontains')
    enabled = filters.BooleanFilter()
    has_update = filters.BooleanFilter()
    
    # Server filters
    server = filters.UUIDFilter(field_name='server__id')
    server_name = filters.CharFilter(field_name='server__name', lookup_expr='icontains')
    
    # Date filters
    installed_after = filters.DateTimeFilter(field_name='installed_at', lookup_expr='gte')
    installed_before = filters.DateTimeFilter(field_name='installed_at', lookup_expr='lte')
    updated_after = filters.DateTimeFilter(field_name='updated_at', lookup_expr='gte')
    updated_before = filters.DateTimeFilter(field_name='updated_at', lookup_expr='lte')
    
    # Dependency filters
    has_dependencies = filters.BooleanFilter(method='filter_has_dependencies')
    depends_on = filters.CharFilter(method='filter_depends_on')
    
    class Meta:
        model = JenkinsPlugin
        fields = ['name', 'enabled', 'has_update', 'server']
    
    def filter_has_dependencies(self, queryset, name, value):
        """Filtre les plugins qui ont des dépendances"""
        if value:
            return queryset.exclude(dependencies=[])
        return queryset.filter(dependencies=[])
    
    def filter_depends_on(self, queryset, name, value):
        """Filtre les plugins qui dépendent d'un autre plugin"""
        return queryset.filter(dependencies__contains=[value])


# ============================================================================
# FILTRES POUR CREDENTIALS JENKINS
# ============================================================================

class JenkinsCredentialFilter(filters.FilterSet):
    """Filtres pour JenkinsCredential"""
    name = filters.CharFilter(lookup_expr='icontains')
    credential_type = filters.ChoiceFilter(choices=JenkinsCredential.CREDENTIAL_TYPE_CHOICES)
    scope = filters.ChoiceFilter(choices=[('global', 'Global'), ('system', 'System')])
    
    # Server filters
    server = filters.UUIDFilter(field_name='server__id')
    server_name = filters.CharFilter(field_name='server__name', lookup_expr='icontains')
    
    # User filters
    username = filters.CharFilter(lookup_expr='icontains')
    
    # Date filters
    synced_after = filters.DateTimeFilter(field_name='synced_at', lookup_expr='gte')
    synced_before = filters.DateTimeFilter(field_name='synced_at', lookup_expr='lte')
    created_after = filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    
    class Meta:
        model = JenkinsCredential
        fields = ['name', 'credential_type', 'scope', 'server', 'username']


# ============================================================================
# FILTRES POUR VUES JENKINS
# ============================================================================

class JenkinsViewFilter(filters.FilterSet):
    """Filtres pour JenkinsView"""
    name = filters.CharFilter(lookup_expr='icontains')
    view_type = filters.CharFilter(lookup_expr='icontains')
    
    # Server filters
    server = filters.UUIDFilter(field_name='server__id')
    server_name = filters.CharFilter(field_name='server__name', lookup_expr='icontains')
    
    # Jobs filters
    min_jobs = filters.NumberFilter(method='filter_min_jobs')
    max_jobs = filters.NumberFilter(method='filter_max_jobs')
    contains_job = filters.CharFilter(method='filter_contains_job')
    
    # Date filters
    created_after = filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    
    class Meta:
        model = JenkinsView
        fields = ['name', 'server']
    
    def filter_min_jobs(self, queryset, name, value):
        """Filtre les vues avec un nombre minimum de jobs"""
        result_ids = []
        for view in queryset:
            if view.jobs and len(view.jobs) >= value:
                result_ids.append(view.id)
        return queryset.filter(id__in=result_ids)
    
    def filter_max_jobs(self, queryset, name, value):
        """Filtre les vues avec un nombre maximum de jobs"""
        result_ids = []
        for view in queryset:
            if view.jobs and len(view.jobs) <= value:
                result_ids.append(view.id)
        return queryset.filter(id__in=result_ids)
    
    def filter_contains_job(self, queryset, name, value):
        """Filtre les vues qui contiennent un job spécifique"""
        result_ids = []
        for view in queryset:
            if view.jobs and value in view.jobs:
                result_ids.append(view.id)
        return queryset.filter(id__in=result_ids)


# ============================================================================
# FILTRES POUR PIPELINES JENKINS
# ============================================================================

class JenkinsPipelineFilter(filters.FilterSet):
    """Filtres pour JenkinsPipeline"""
    name = filters.CharFilter(lookup_expr='icontains')
    description = filters.CharFilter(lookup_expr='icontains')
    
    # Jobs filters
    has_job = filters.UUIDFilter(method='filter_has_job')
    job_name = filters.CharFilter(method='filter_job_name')
    min_jobs = filters.NumberFilter(method='filter_min_jobs')
    max_jobs = filters.NumberFilter(method='filter_max_jobs')
    
    # Created by
    created_by = filters.UUIDFilter(field_name='created_by__id')
    created_by_name = filters.CharFilter(field_name='created_by__email', lookup_expr='icontains')
    
    # Date filters
    created_after = filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    updated_after = filters.DateTimeFilter(field_name='updated_at', lookup_expr='gte')
    updated_before = filters.DateTimeFilter(field_name='updated_at', lookup_expr='lte')
    
    # Parameter filters
    has_parameters = filters.BooleanFilter(method='filter_has_parameters')
    parameter_key = filters.CharFilter(method='filter_parameter_key')
    
    # Environment filters
    has_environment = filters.BooleanFilter(method='filter_has_environment')
    env_key = filters.CharFilter(method='filter_env_key')
    
    class Meta:
        model = JenkinsPipeline
        fields = ['name', 'created_by']
    
    def filter_has_job(self, queryset, name, value):
        """Filtre les pipelines qui contiennent un job spécifique"""
        return queryset.filter(jobs__id=value)
    
    def filter_job_name(self, queryset, name, value):
        """Filtre les pipelines qui contiennent un job (par nom)"""
        return queryset.filter(jobs__name__icontains=value).distinct()
    
    def filter_min_jobs(self, queryset, name, value):
        """Filtre les pipelines avec un nombre minimum de jobs"""
        return queryset.annotate(jobs_count=Count('jobs')).filter(jobs_count__gte=value)
    
    def filter_max_jobs(self, queryset, name, value):
        """Filtre les pipelines avec un nombre maximum de jobs"""
        return queryset.annotate(jobs_count=Count('jobs')).filter(jobs_count__lte=value)
    
    def filter_has_parameters(self, queryset, name, value):
        """Filtre les pipelines qui ont des paramètres"""
        if value:
            return queryset.exclude(parameters={})
        return queryset.filter(parameters={})
    
    def filter_parameter_key(self, queryset, name, value):
        """Filtre les pipelines qui ont une clé de paramètre spécifique"""
        result_ids = []
        for pipeline in queryset:
            if pipeline.parameters and value in pipeline.parameters:
                result_ids.append(pipeline.id)
        return queryset.filter(id__in=result_ids)
    
    def filter_has_environment(self, queryset, name, value):
        """Filtre les pipelines qui ont des variables d'environnement"""
        if value:
            return queryset.exclude(environment={})
        return queryset.filter(environment={})
    
    def filter_env_key(self, queryset, name, value):
        """Filtre les pipelines qui ont une variable d'environnement spécifique"""
        result_ids = []
        for pipeline in queryset:
            if pipeline.environment and value in pipeline.environment:
                result_ids.append(pipeline.id)
        return queryset.filter(id__in=result_ids)