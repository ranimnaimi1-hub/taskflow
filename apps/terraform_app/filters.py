# apps/terraform_app/filters.py
"""
Terraform App Filters - Filtres personnalisés pour l'API
"""
import django_filters
from django_filters import rest_framework as filters
from django.db import models
from django.db.models import F, Sum, Value, IntegerField
from django.db.models.functions import Coalesce
from .models import (
    TerraformConfig, TerraformPlan, TerraformApply, TerraformState,
    TerraformModule, TerraformProvider, TerraformVariable, TerraformCredential
)


# ============================================================================
# FILTRES POUR TERRAFORM CONFIG
# ============================================================================

class TerraformConfigFilter(filters.FilterSet):
    """Filtres pour TerraformConfig"""
    name = filters.CharFilter(lookup_expr='icontains')
    description = filters.CharFilter(lookup_expr='icontains')
    provider = filters.ChoiceFilter(choices=TerraformConfig.PROVIDER_CHOICES)
    status = filters.ChoiceFilter(choices=TerraformConfig.STATUS_CHOICES)
    version = filters.CharFilter(lookup_expr='icontains')
    
    # Date filters
    created_after = filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    updated_after = filters.DateTimeFilter(field_name='updated_at', lookup_expr='gte')
    updated_before = filters.DateTimeFilter(field_name='updated_at', lookup_expr='lte')
    
    # Relation filters
    site = filters.UUIDFilter(field_name='site__id')
    site_name = filters.CharFilter(field_name='site__name', lookup_expr='icontains')
    cluster = filters.UUIDFilter(field_name='cluster__id')
    cluster_name = filters.CharFilter(field_name='cluster__name', lookup_expr='icontains')
    tenant = filters.UUIDFilter(field_name='tenant__id')
    tenant_name = filters.CharFilter(field_name='tenant__name', lookup_expr='icontains')
    created_by = filters.UUIDFilter(field_name='created_by__id')
    created_by_name = filters.CharFilter(field_name='created_by__email', lookup_expr='icontains')
    
    # Custom filters
    min_apply_count = filters.NumberFilter(field_name='apply_count', lookup_expr='gte')
    max_apply_count = filters.NumberFilter(field_name='apply_count', lookup_expr='lte')
    last_apply_status = filters.CharFilter(field_name='last_apply_status', lookup_expr='iexact')
    last_apply_after = filters.DateTimeFilter(field_name='last_apply_at', lookup_expr='gte')
    last_apply_before = filters.DateTimeFilter(field_name='last_apply_at', lookup_expr='lte')
    
    # Backend filters
    backend_type = filters.CharFilter(field_name='backend_type', lookup_expr='icontains')
    
    # JSON field filters
    has_variables = filters.BooleanFilter(method='filter_has_variables')
    has_config_files = filters.BooleanFilter(method='filter_has_config_files')
    
    class Meta:
        model = TerraformConfig
        fields = [
            'name', 'provider', 'status', 'version', 'site', 'cluster', 'tenant',
            'created_by', 'backend_type'
        ]
    
    def filter_has_variables(self, queryset, name, value):
        """Filtre les configurations qui ont des variables définies"""
        if value:
            return queryset.exclude(variables={})
        return queryset.filter(variables={})
    
    def filter_has_config_files(self, queryset, name, value):
        """Filtre les configurations qui ont des fichiers supplémentaires"""
        if value:
            return queryset.exclude(config_files={})
        return queryset.filter(config_files={})


# ============================================================================
# FILTRES POUR TERRAFORM PLAN
# ============================================================================

class TerraformPlanFilter(filters.FilterSet):
    """Filtres pour TerraformPlan"""
    config = filters.UUIDFilter(field_name='config__id')
    config_name = filters.CharFilter(field_name='config__name', lookup_expr='icontains')
    status = filters.ChoiceFilter(choices=TerraformPlan.PLAN_STATUS_CHOICES)
    has_changes = filters.BooleanFilter()
    
    # Resource counts - ✅ CORRIGÉ: utilisation de field_name
    min_resources_add = filters.NumberFilter(field_name='resources_add', lookup_expr='gte')
    max_resources_add = filters.NumberFilter(field_name='resources_add', lookup_expr='lte')
    min_resources_change = filters.NumberFilter(field_name='resources_change', lookup_expr='gte')
    max_resources_change = filters.NumberFilter(field_name='resources_change', lookup_expr='lte')
    min_resources_destroy = filters.NumberFilter(field_name='resources_destroy', lookup_expr='gte')
    max_resources_destroy = filters.NumberFilter(field_name='resources_destroy', lookup_expr='lte')
    
    # ✅ CORRIGÉ: Filtres personnalisés avec méthode
    total_resources_min = filters.NumberFilter(method='filter_total_resources_min')
    total_resources_max = filters.NumberFilter(method='filter_total_resources_max')
    
    # Date filters
    created_after = filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    started_after = filters.DateTimeFilter(field_name='started_at', lookup_expr='gte')
    started_before = filters.DateTimeFilter(field_name='started_at', lookup_expr='lte')
    completed_after = filters.DateTimeFilter(field_name='completed_at', lookup_expr='gte')
    completed_before = filters.DateTimeFilter(field_name='completed_at', lookup_expr='lte')
    
    # Duration filters
    min_duration = filters.NumberFilter(field_name='duration', lookup_expr='gte')
    max_duration = filters.NumberFilter(field_name='duration', lookup_expr='lte')
    
    # User filters
    executed_by = filters.UUIDFilter(field_name='executed_by__id')
    executed_by_name = filters.CharFilter(field_name='executed_by__email', lookup_expr='icontains')
    
    # Return code
    return_code = filters.NumberFilter()
    is_success = filters.BooleanFilter(method='filter_is_success')
    
    class Meta:
        model = TerraformPlan
        fields = ['config', 'status', 'has_changes', 'executed_by', 'return_code']
    
    def filter_total_resources_min(self, queryset, name, value):
        """Filtre les plans avec un nombre total de ressources minimum"""
        # ✅ CORRIGÉ: Utilisation de F() expressions pour le calcul
        return queryset.annotate(
            total_resources=(
                Coalesce(F('resources_add'), Value(0)) + 
                Coalesce(F('resources_change'), Value(0)) + 
                Coalesce(F('resources_destroy'), Value(0))
            )
        ).filter(total_resources__gte=value)
    
    def filter_total_resources_max(self, queryset, name, value):
        """Filtre les plans avec un nombre total de ressources maximum"""
        return queryset.annotate(
            total_resources=(
                Coalesce(F('resources_add'), Value(0)) + 
                Coalesce(F('resources_change'), Value(0)) + 
                Coalesce(F('resources_destroy'), Value(0))
            )
        ).filter(total_resources__lte=value)
    
    def filter_is_success(self, queryset, name, value):
        """Filtre les plans qui ont réussi (return_code 0)"""
        if value:
            return queryset.filter(return_code=0)
        return queryset.exclude(return_code=0)


# ============================================================================
# FILTRES POUR TERRAFORM APPLY
# ============================================================================

class TerraformApplyFilter(filters.FilterSet):
    """Filtres pour TerraformApply"""
    config = filters.UUIDFilter(field_name='config__id')
    config_name = filters.CharFilter(field_name='config__name', lookup_expr='icontains')
    plan = filters.UUIDFilter(field_name='plan__id')
    plan_id = filters.CharFilter(field_name='plan__plan_id', lookup_expr='icontains')
    status = filters.ChoiceFilter(choices=TerraformApply.APPLY_STATUS_CHOICES)
    
    # Date filters
    created_after = filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    started_after = filters.DateTimeFilter(field_name='started_at', lookup_expr='gte')
    started_before = filters.DateTimeFilter(field_name='started_at', lookup_expr='lte')
    completed_after = filters.DateTimeFilter(field_name='completed_at', lookup_expr='gte')
    completed_before = filters.DateTimeFilter(field_name='completed_at', lookup_expr='lte')
    
    # Duration filters
    min_duration = filters.NumberFilter(field_name='duration', lookup_expr='gte')
    max_duration = filters.NumberFilter(field_name='duration', lookup_expr='lte')
    
    # User filters
    executed_by = filters.UUIDFilter(field_name='executed_by__id')
    executed_by_name = filters.CharFilter(field_name='executed_by__email', lookup_expr='icontains')
    
    # Return code
    return_code = filters.NumberFilter()
    is_success = filters.BooleanFilter(method='filter_is_success')
    
    # Has outputs
    has_outputs = filters.BooleanFilter(method='filter_has_outputs')
    
    class Meta:
        model = TerraformApply
        fields = ['config', 'plan', 'status', 'executed_by', 'return_code']
    
    def filter_is_success(self, queryset, name, value):
        """Filtre les apply qui ont réussi (return_code 0)"""
        if value:
            return queryset.filter(return_code=0, status='completed')
        return queryset.exclude(return_code=0) | queryset.exclude(status='completed')
    
    def filter_has_outputs(self, queryset, name, value):
        """Filtre les apply qui ont des outputs"""
        if value:
            return queryset.exclude(outputs={})
        return queryset.filter(outputs={})


# ============================================================================
# FILTRES POUR TERRAFORM STATE
# ============================================================================

class TerraformStateFilter(filters.FilterSet):
    """Filtres pour TerraformState"""
    config = filters.UUIDFilter(field_name='config__id')
    config_name = filters.CharFilter(field_name='config__name', lookup_expr='icontains')
    apply = filters.UUIDFilter(field_name='apply__id')
    
    # Version filters
    version = filters.NumberFilter()
    min_version = filters.NumberFilter(field_name='version', lookup_expr='gte')
    max_version = filters.NumberFilter(field_name='version', lookup_expr='lte')
    
    # Lineage
    lineage = filters.CharFilter(lookup_expr='icontains')
    
    # Resource count
    min_resources = filters.NumberFilter(field_name='resources_count', lookup_expr='gte')
    max_resources = filters.NumberFilter(field_name='resources_count', lookup_expr='lte')
    
    # Date filters
    captured_after = filters.DateTimeFilter(field_name='captured_at', lookup_expr='gte')
    captured_before = filters.DateTimeFilter(field_name='captured_at', lookup_expr='lte')
    created_after = filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    
    # Resource type presence
    has_resource_type = filters.CharFilter(method='filter_has_resource_type')
    
    class Meta:
        model = TerraformState
        fields = ['config', 'apply', 'version', 'lineage']
    
    def filter_has_resource_type(self, queryset, name, value):
        """Filtre les états qui contiennent un type de ressource spécifique"""
        # ✅ CORRIGÉ: Utilisation de filter sur JSONField
        return queryset.filter(resources_summary__by_type__has_key=value)


# ============================================================================
# FILTRES POUR TERRAFORM MODULE
# ============================================================================

class TerraformModuleFilter(filters.FilterSet):
    """Filtres pour TerraformModule"""
    name = filters.CharFilter(lookup_expr='icontains')
    namespace = filters.CharFilter(lookup_expr='icontains')
    source = filters.ChoiceFilter(choices=TerraformModule.SOURCE_CHOICES)
    version = filters.CharFilter(lookup_expr='icontains')
    
    # Source filters
    source_url = filters.CharFilter(lookup_expr='icontains')
    source_version = filters.CharFilter(lookup_expr='icontains')
    
    # Provider presence
    has_provider = filters.CharFilter(method='filter_has_provider')
    
    # Stats filters
    min_downloads = filters.NumberFilter(field_name='download_count', lookup_expr='gte')
    max_downloads = filters.NumberFilter(field_name='download_count', lookup_expr='lte')
    min_usage = filters.NumberFilter(field_name='used_in_configs', lookup_expr='gte')
    max_usage = filters.NumberFilter(field_name='used_in_configs', lookup_expr='lte')
    
    # Date filters
    created_after = filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    
    class Meta:
        model = TerraformModule
        fields = ['name', 'namespace', 'source', 'version']
    
    def filter_has_provider(self, queryset, name, value):
        """Filtre les modules qui nécessitent un provider spécifique"""
        # ✅ CORRIGÉ: Utilisation de filter sur JSONField
        return queryset.filter(required_providers__has_key=value)


# ============================================================================
# FILTRES POUR TERRAFORM PROVIDER
# ============================================================================

class TerraformProviderFilter(filters.FilterSet):
    """Filtres pour TerraformProvider"""
    name = filters.CharFilter(lookup_expr='icontains')
    version = filters.CharFilter(lookup_expr='icontains')
    source = filters.CharFilter(lookup_expr='icontains')
    
    # Date filters
    created_after = filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    
    class Meta:
        model = TerraformProvider
        fields = ['name', 'version', 'source']


# ============================================================================
# FILTRES POUR TERRAFORM VARIABLE
# ============================================================================

class TerraformVariableFilter(filters.FilterSet):
    """Filtres pour TerraformVariable"""
    config = filters.UUIDFilter(field_name='config__id')
    config_name = filters.CharFilter(field_name='config__name', lookup_expr='icontains')
    name = filters.CharFilter(lookup_expr='icontains')
    environment = filters.CharFilter(lookup_expr='icontains')
    is_sensitive = filters.BooleanFilter()
    
    # Created by
    created_by = filters.UUIDFilter(field_name='created_by__id')
    created_by_name = filters.CharFilter(field_name='created_by__email', lookup_expr='icontains')
    
    # Date filters
    created_after = filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    
    class Meta:
        model = TerraformVariable
        fields = ['config', 'name', 'environment', 'is_sensitive', 'created_by']


# ============================================================================
# FILTRES POUR TERRAFORM CREDENTIAL
# ============================================================================

class TerraformCredentialFilter(filters.FilterSet):
    """Filtres pour TerraformCredential"""
    name = filters.CharFilter(lookup_expr='icontains')
    provider = filters.ChoiceFilter(choices=TerraformCredential.CREDENTIAL_TYPE_CHOICES)
    description = filters.CharFilter(lookup_expr='icontains')
    
    # Provider specific filters
    aws_profile = filters.CharFilter(lookup_expr='icontains')
    aws_region = filters.CharFilter(lookup_expr='icontains')
    azure_subscription_id = filters.CharFilter(lookup_expr='icontains')
    azure_tenant_id = filters.CharFilter(lookup_expr='icontains')
    gcp_project = filters.CharFilter(lookup_expr='icontains')
    ssh_user = filters.CharFilter(lookup_expr='icontains')
    
    # Relations
    config = filters.UUIDFilter(method='filter_config')
    config_name = filters.CharFilter(method='filter_config_name')
    
    # Created by
    created_by = filters.UUIDFilter(field_name='created_by__id')
    created_by_name = filters.CharFilter(field_name='created_by__email', lookup_expr='icontains')
    
    # Date filters
    created_after = filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    
    class Meta:
        model = TerraformCredential
        fields = ['name', 'provider', 'created_by']
    
    def filter_config(self, queryset, name, value):
        """Filtre les credentials utilisés par une configuration spécifique"""
        return queryset.filter(configs__id=value)
    
    def filter_config_name(self, queryset, name, value):
        """Filtre les credentials utilisés par une configuration (par nom)"""
        return queryset.filter(configs__name__icontains=value).distinct()