# apps/inventory/urls.py
"""
Inventory URLs - Configuration des routes API
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *

router = DefaultRouter()

# Hiérarchie
router.register(r'regions', RegionViewSet)
router.register(r'sites', SiteViewSet)
router.register(r'locations', LocationViewSet)

# Manufacturers et Device Types
router.register(r'manufacturers', ManufacturerViewSet)
router.register(r'device-types', DeviceTypeViewSet)

# Racks
router.register(r'racks', RackViewSet)

# Devices
router.register(r'devices', DeviceViewSet)

# Interfaces
router.register(r'interfaces', InterfaceViewSet)

# IPAM
router.register(r'vrfs', VRFViewSet)
router.register(r'route-targets', RouteTargetViewSet)
router.register(r'prefixes', PrefixViewSet)
router.register(r'ip-addresses', IPAddressViewSet)

# VLANs
router.register(r'vlan-groups', VLANGroupViewSet)
router.register(r'vlans', VLANViewSet)

# Câbles
router.register(r'cables', CableViewSet)
router.register(r'breakout-cables', BreakoutCableViewSet)

# Power
router.register(r'power-ports', PowerPortViewSet)
router.register(r'power-feeds', PowerFeedViewSet)

# Circuits
router.register(r'providers', ProviderViewSet)
router.register(r'circuits', CircuitViewSet)
router.register(r'circuit-terminations', CircuitTerminationViewSet)

# Routing
router.register(r'asns', ASNViewSet)
router.register(r'fhrp-groups', FHRPGroupViewSet)
router.register(r'bgp-sessions', BGPSessionViewSet)

# Virtualisation
router.register(r'clusters', ClusterViewSet)
router.register(r'virtual-machines', VirtualMachineViewSet)

# Tenancy
router.register(r'tenants', TenantViewSet)
router.register(r'contacts', ContactViewSet)
router.register(r'tenant-assignments', TenantAssignmentViewSet)

# L2VPN
router.register(r'l2vpns', L2VPNViewSet)

# Dashboard
router.register(r'dashboard', InventoryDashboardViewSet, basename='inventory-dashboard')

urlpatterns = [
    path('', include(router.urls)),
]