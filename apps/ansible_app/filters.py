# apps/ansible_app/filters.py
"""
Ansible App Filters - Filtres personnalisés pour l'API
"""
import django_filters
from django_filters import rest_framework as filters
from django.db import models
from .models import *


class AnsibleInventoryFilter(filters.FilterSet):
    """Filtres pour AnsibleInventory"""
    name = filters.CharFilter(lookup_expr='icontains')
    created_after = filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    min_hosts = filters.NumberFilter(method='filter_min_hosts')
    has_devices = filters.BooleanFilter(method='filter_has_devices')
    has_sites = filters.BooleanFilter(method='filter_has_sites')
    
    class Meta:
        model = AnsibleInventory
        fields = ['inventory_type', 'format', 'is_active', 'created_by']
    
    def filter_min_hosts(self, queryset, name, value):
        # Cette méthode doit retourner un queryset, pas une liste
        result_ids = []
        for inv in queryset:
            if inv.get_hosts_count() >= value:
                result_ids.append(inv.id)
        return queryset.filter(id__in=result_ids)
    
    def filter_has_devices(self, queryset, name, value):
        if value:
            return queryset.filter(devices__isnull=False).distinct()
        return queryset.filter(devices__isnull=True).distinct()
    
    def filter_has_sites(self, queryset, name, value):
        if value:
            return queryset.filter(sites__isnull=False).distinct()
        return queryset.filter(sites__isnull=True).distinct()


class PlaybookFilter(filters.FilterSet):
    """Filtres pour Playbook"""
    name = filters.CharFilter(lookup_expr='icontains')
    created_after = filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    min_success_rate = filters.NumberFilter(method='filter_min_success_rate')
    tag = filters.CharFilter(field_name='tags', lookup_expr='contains')
    created_by = filters.UUIDFilter(field_name='created_by__id')
    
    class Meta:
        model = Playbook
        fields = ['status', 'visibility', 'inventory']
    
    def filter_min_success_rate(self, queryset, name, value):
        # Cette méthode doit retourner un queryset, pas une liste
        result_ids = []
        for p in queryset:
            if p.success_rate >= value:
                result_ids.append(p.id)
        return queryset.filter(id__in=result_ids)


class PlaybookExecutionFilter(filters.FilterSet):
    """Filtres pour PlaybookExecution"""
    playbook = filters.UUIDFilter(field_name='playbook__id')
    playbook_name = filters.CharFilter(field_name='playbook__name', lookup_expr='icontains')
    executed_by = filters.UUIDFilter(field_name='executed_by__id')
    started_after = filters.DateTimeFilter(field_name='started_at', lookup_expr='gte')
    started_before = filters.DateTimeFilter(field_name='started_at', lookup_expr='lte')
    completed_after = filters.DateTimeFilter(field_name='completed_at', lookup_expr='gte')
    completed_before = filters.DateTimeFilter(field_name='completed_at', lookup_expr='lte')
    min_duration = filters.NumberFilter(field_name='duration', lookup_expr='gte')
    max_duration = filters.NumberFilter(field_name='duration', lookup_expr='lte')
    
    class Meta:
        model = PlaybookExecution
        fields = ['playbook', 'status', 'check_mode', 'executed_by']


class PlaybookScheduleFilter(filters.FilterSet):
    """Filtres pour PlaybookSchedule - AJOUTÉ"""
    name = filters.CharFilter(lookup_expr='icontains')
    playbook = filters.UUIDFilter(field_name='playbook__id')
    playbook_name = filters.CharFilter(field_name='playbook__name', lookup_expr='icontains')
    created_by = filters.UUIDFilter(field_name='created_by__id')
    next_run_after = filters.DateTimeFilter(field_name='next_run', lookup_expr='gte')
    next_run_before = filters.DateTimeFilter(field_name='next_run', lookup_expr='lte')
    is_active = filters.BooleanFilter(method='filter_is_active')
    
    class Meta:
        model = PlaybookSchedule
        fields = ['status', 'schedule_type', 'playbook']
    
    def filter_is_active(self, queryset, name, value):
        if value:
            return queryset.filter(status='active')
        return queryset.exclude(status='active')


class AnsibleRoleFilter(filters.FilterSet):
    """Filtres pour AnsibleRole"""
    name = filters.CharFilter(lookup_expr='icontains')
    namespace = filters.CharFilter(lookup_expr='icontains')
    
    class Meta:
        model = AnsibleRole
        fields = ['source', 'namespace']


class AnsibleCollectionFilter(filters.FilterSet):
    """Filtres pour AnsibleCollection - AJOUTÉ"""
    name = filters.CharFilter(lookup_expr='icontains')
    namespace = filters.CharFilter(lookup_expr='icontains')
    
    class Meta:
        model = AnsibleCollection
        fields = ['namespace']


class AnsibleCredentialFilter(filters.FilterSet):
    """Filtres pour AnsibleCredential"""
    name = filters.CharFilter(lookup_expr='icontains')
    
    class Meta:
        model = AnsibleCredential
        fields = ['credential_type']


class AnsibleTaskFilter(filters.FilterSet):
    """Filtres pour AnsibleTask"""
    name = filters.CharFilter(lookup_expr='icontains')
    created_by = filters.UUIDFilter(field_name='created_by__id')
    tag = filters.CharFilter(method='filter_by_tag', label='Tag')
    
    class Meta:
        model = AnsibleTask
        fields = ['created_by']  # N'incluez pas 'tags' directement
    
    def filter_by_tag(self, queryset, name, value):
        """Filtre les tâches qui contiennent un tag spécifique"""
        # Pour PostgreSQL (JSONField)
        return queryset.filter(tags__contains=[value])