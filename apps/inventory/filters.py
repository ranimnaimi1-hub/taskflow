# apps/inventory/filters.py
"""
Inventory Filters - Filtres personnalisés pour l'API
"""
import django_filters
from django_filters import rest_framework as filters
from django.db import models
from .models import *


class SiteFilter(filters.FilterSet):
    """Filtres pour Site"""
    region = filters.UUIDFilter(field_name='region__id')
    region_name = filters.CharFilter(field_name='region__name', lookup_expr='icontains')
    parent = filters.UUIDFilter(field_name='parent__id')
    created_after = filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    has_racks = filters.BooleanFilter(method='filter_has_racks')
    has_devices = filters.BooleanFilter(method='filter_has_devices')
    
    class Meta:
        model = Site
        fields = ['site_type', 'status', 'country', 'region']
    
    def filter_has_racks(self, queryset, name, value):
        if value:
            return queryset.filter(racks__isnull=False).distinct()
        return queryset.filter(racks__isnull=True).distinct()
    
    def filter_has_devices(self, queryset, name, value):
        if value:
            return queryset.filter(devices__isnull=False).distinct()
        return queryset.filter(devices__isnull=True).distinct()


class DeviceFilter(filters.FilterSet):
    """Filtres pour Device"""
    site = filters.UUIDFilter(field_name='site__id')
    site_name = filters.CharFilter(field_name='site__name', lookup_expr='icontains')
    rack = filters.UUIDFilter(field_name='rack__id')
    device_type = filters.UUIDFilter(field_name='device_type__id')
    device_class = filters.ChoiceFilter(field_name='device_type__device_class', choices=DeviceType.DEVICE_CLASS_CHOICES)
    manufacturer = filters.UUIDFilter(field_name='device_type__manufacturer__id')
    manufacturer_name = filters.CharFilter(field_name='device_type__manufacturer__name', lookup_expr='icontains')
    tenant = filters.UUIDFilter(field_name='tenant__id')
    owner = filters.UUIDFilter(field_name='owner__id')
    status = filters.ChoiceFilter(choices=Device.STATUS_CHOICES)
    role = filters.ChoiceFilter(choices=Device.ROLE_CHOICES)
    is_reachable = filters.BooleanFilter(method='filter_is_reachable')
    has_interface = filters.BooleanFilter(method='filter_has_interface')
    has_ip = filters.BooleanFilter(method='filter_has_ip')
    created_after = filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    last_seen_after = filters.DateTimeFilter(field_name='last_seen', lookup_expr='gte')
    cpu_gt = filters.NumberFilter(field_name='cpu_usage', lookup_expr='gt')
    cpu_lt = filters.NumberFilter(field_name='cpu_usage', lookup_expr='lt')
    memory_gt = filters.NumberFilter(field_name='memory_usage', lookup_expr='gt')
    memory_lt = filters.NumberFilter(field_name='memory_usage', lookup_expr='lt')
    
    class Meta:
        model = Device
        fields = ['site', 'rack', 'device_type', 'status', 'role', 'tenant']
    
    def filter_is_reachable(self, queryset, name, value):
        from django.utils import timezone
        from datetime import timedelta
        
        if value:
            return queryset.filter(last_seen__gte=timezone.now() - timedelta(minutes=5))
        return queryset.filter(last_seen__lt=timezone.now() - timedelta(minutes=5))
    
    def filter_has_interface(self, queryset, name, value):
        if value:
            return queryset.filter(interfaces__isnull=False).distinct()
        return queryset.filter(interfaces__isnull=True).distinct()
    
    def filter_has_ip(self, queryset, name, value):
        if value:
            return queryset.filter(interfaces__ip_addresses__isnull=False).distinct()
        return queryset.filter(interfaces__ip_addresses__isnull=True).distinct()


class InterfaceFilter(filters.FilterSet):
    """Filtres pour Interface"""
    device = filters.UUIDFilter(field_name='device__id')
    site = filters.UUIDFilter(field_name='device__site__id')
    status = filters.ChoiceFilter(choices=Interface.STATUS_CHOICES)
    interface_type = filters.ChoiceFilter(choices=Interface.INTERFACE_TYPE_CHOICES)
    enabled = filters.BooleanFilter()
    has_ip = filters.BooleanFilter(method='filter_has_ip')
    has_cable = filters.BooleanFilter(method='filter_has_cable')
    speed_gt = filters.NumberFilter(field_name='speed', lookup_expr='gt')
    speed_lt = filters.NumberFilter(field_name='speed', lookup_expr='lt')
    
    class Meta:
        model = Interface
        fields = ['device', 'site', 'status', 'interface_type', 'enabled']
    
    def filter_has_ip(self, queryset, name, value):
        if value:
            return queryset.filter(ip_addresses__isnull=False).distinct()
        return queryset.filter(ip_addresses__isnull=True).distinct()
    
    def filter_has_cable(self, queryset, name, value):
        if value:
            return queryset.filter(
                models.Q(cables_a__isnull=False) | models.Q(cables_b__isnull=False)
            ).distinct()
        return queryset.filter(cables_a__isnull=True, cables_b__isnull=True).distinct()


class IPAddressFilter(filters.FilterSet):
    """Filtres pour IPAddress"""
    vrf = filters.UUIDFilter(field_name='vrf__id')
    vrf_name = filters.CharFilter(field_name='vrf__name', lookup_expr='icontains')
    device = filters.UUIDFilter(field_name='interface__device__id')
    site = filters.UUIDFilter(field_name='interface__device__site__id')
    interface = filters.UUIDFilter(field_name='interface__id')
    status = filters.ChoiceFilter(choices=IPAddress.STATUS_CHOICES)
    ip_type = filters.ChoiceFilter(choices=IPAddress.IP_TYPE_CHOICES)
    family = filters.ChoiceFilter(choices=IPAddress.FAMILY_CHOICES)
    tenant = filters.UUIDFilter(field_name='tenant__id')
    network = filters.CharFilter(method='filter_network')
    
    class Meta:
        model = IPAddress
        fields = ['vrf', 'device', 'site', 'interface', 'status', 'ip_type', 'family', 'tenant']
    
    def filter_network(self, queryset, name, value):
        """Filtre par réseau (CIDR)"""
        try:
            import ipaddress
            network = ipaddress.ip_network(value, strict=False)
            return [ip for ip in queryset if ipaddress.ip_address(ip.address) in network]
        except:
            return queryset.none()


class PrefixFilter(filters.FilterSet):
    """Filtres pour Prefix"""
    vrf = filters.UUIDFilter(field_name='vrf__id')
    vrf_name = filters.CharFilter(field_name='vrf__name', lookup_expr='icontains')
    site = filters.UUIDFilter(field_name='site__id')
    status = filters.ChoiceFilter(choices=Prefix.STATUS_CHOICES)
    family = filters.ChoiceFilter(choices=Prefix.FAMILY_CHOICES)
    tenant = filters.UUIDFilter(field_name='tenant__id')
    is_pool = filters.BooleanFilter()
    min_prefix_length = filters.NumberFilter(field_name='prefix_length', lookup_expr='gte')
    max_prefix_length = filters.NumberFilter(field_name='prefix_length', lookup_expr='lte')
    contains = filters.CharFilter(method='filter_contains')
    
    class Meta:
        model = Prefix
        fields = ['vrf', 'site', 'status', 'family', 'tenant', 'is_pool']
    
    def filter_contains(self, queryset, name, value):
        """Filtre les préfixes qui contiennent une IP ou sous-réseau"""
        try:
            import ipaddress
            obj = ipaddress.ip_network(value, strict=False)
            return [p for p in queryset if obj.subnet_of(ipaddress.ip_network(p.prefix))]
        except:
            return queryset.none()