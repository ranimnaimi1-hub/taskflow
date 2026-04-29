# apps/inventory/views.py
"""
Inventory Views - Ultra Professional
Vues API pour tous les modèles
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import filters as drf_filters  # Renommer pour éviter les conflits
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta

from apps.core.permissions import IsAdmin, CanManageInventory
from apps.core.pagination import StandardPagination
from apps.core.responses import success_response, created_response, error_response

from .models import *
from .serializers import *
from .filters import *
from .utils.ipam_utils import IPAMManager
from .utils.svg_renderer import SVGRackRenderer


# ============================================================================
# HIÉRARCHIE
# ============================================================================

class RegionViewSet(viewsets.ModelViewSet):
    queryset = Region.objects.all()
    serializer_class = RegionSerializer
    permission_classes = [IsAuthenticated, CanManageInventory]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]  # Correction
    search_fields = ['name', 'code']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']


class SiteViewSet(viewsets.ModelViewSet):
    queryset = Site.objects.select_related('region', 'parent').prefetch_related('racks', 'devices')
    serializer_class = SiteSerializer
    permission_classes = [IsAuthenticated, CanManageInventory]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]  # Correction
    filterset_class = SiteFilter
    search_fields = ['name', 'code', 'city', 'country']
    ordering_fields = ['name', 'created_at', 'status']
    ordering = ['name']
    
    @action(detail=True, methods=['get'])
    def dashboard(self, request, pk=None):
        """Tableau de bord du site"""
        site = self.get_object()
        
        devices = site.devices.all()
        racks = site.racks.all()
        vlans = site.vlans.all()
        prefixes = site.prefixes.all()
        
        data = {
            'id': site.id,
            'name': site.name,
            'code': site.code,
            'statistics': {
                'total_devices': devices.count(),
                'active_devices': devices.filter(status='active').count(),
                'total_racks': racks.count(),
                'total_vlans': vlans.count(),
                'total_prefixes': prefixes.count(),
                'total_ip_addresses': IPAddress.objects.filter(interface__device__site=site).count(),
            },
            'recent_devices': DeviceListSerializer(devices.order_by('-created_at')[:5], many=True).data,
            'recent_alerts': []  # À connecter avec app alerts
        }
        
        return success_response(data, "Site dashboard retrieved")
    
    @action(detail=True, methods=['get'])
    def topology(self, request, pk=None):
        """Topologie réseau du site"""
        site = self.get_object()
        
        # Récupérer tous les équipements et leurs connexions
        devices = site.devices.all()
        cables = Cable.objects.filter(
            Q(interface_a__device__in=devices) | Q(interface_b__device__in=devices)
        ).distinct()
        
        # Construire la topologie
        nodes = []
        links = []
        
        for device in devices:
            nodes.append({
                'id': str(device.id),
                'name': device.name,
                'type': device.device_type.device_class,
                'status': device.status
            })
        
        for cable in cables:
            links.append({
                'source': str(cable.interface_a.device.id),
                'target': str(cable.interface_b.device.id),
                'type': cable.cable_type,
                'interface_a': cable.interface_a.name,
                'interface_b': cable.interface_b.name
            })
        
        return success_response({
            'nodes': nodes,
            'links': links
        }, "Site topology retrieved")


class LocationViewSet(viewsets.ModelViewSet):
    queryset = Location.objects.select_related('site', 'parent')
    serializer_class = LocationSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]  # Correction
    filterset_fields = ['site', 'location_type']
    search_fields = ['name']


# ============================================================================
# MANUFACTURERS ET DEVICE TYPES
# ============================================================================

class ManufacturerViewSet(viewsets.ModelViewSet):
    queryset = Manufacturer.objects.all()
    serializer_class = ManufacturerSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination
    filter_backends = [drf_filters.SearchFilter, drf_filters.OrderingFilter]  # Correction
    search_fields = ['name']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']


class DeviceTypeViewSet(viewsets.ModelViewSet):
    queryset = DeviceType.objects.select_related('manufacturer')
    serializer_class = DeviceTypeSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]  # Correction
    filterset_fields = ['device_class', 'manufacturer']
    search_fields = ['name', 'manufacturer__name', 'model']
    ordering_fields = ['manufacturer', 'model', 'created_at']
    ordering = ['manufacturer', 'model']


# ============================================================================
# RACKS
# ============================================================================

class RackViewSet(viewsets.ModelViewSet):
    queryset = Rack.objects.select_related('site', 'location')
    serializer_class = RackSerializer
    permission_classes = [IsAuthenticated, CanManageInventory]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]  # Correction
    filterset_fields = ['site', 'status', 'rack_type']
    search_fields = ['name']
    ordering_fields = ['name', 'created_at']
    ordering = ['site', 'name']
    
    @action(detail=True, methods=['get'])
    def detail(self, request, pk=None):
        """Détails du rack avec équipements"""
        rack = self.get_object()
        serializer = RackDetailSerializer(rack)
        return success_response(serializer.data, "Rack details retrieved")
    
    @action(detail=True, methods=['get'])
    def svg(self, request, pk=None):
        """Génère le SVG du rack"""
        rack = self.get_object()
        renderer = SVGRackRenderer(rack)
        svg = renderer.render()
        return Response(svg, content_type='image/svg+xml')
    
    @action(detail=True, methods=['post'])
    def generate_svg(self, request, pk=None):
        """Génère et sauvegarde le SVG du rack"""
        rack = self.get_object()
        renderer = SVGRackRenderer(rack)
        rack.svg_elevation = renderer.render()
        rack.save()
        return success_response({"svg": rack.svg_elevation}, "SVG generated")


# ============================================================================
# DEVICES
# ============================================================================

class DeviceViewSet(viewsets.ModelViewSet):
    queryset = Device.objects.select_related(
        'site', 'device_type', 'rack', 'tenant', 'owner'
    ).prefetch_related('interfaces', 'power_ports')
    permission_classes = [IsAuthenticated, CanManageInventory]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]  # Correction
    filterset_class = DeviceFilter
    search_fields = ['name', 'hostname', 'management_ip', 'serial_number']
    ordering_fields = ['name', 'created_at', 'last_seen', 'status']
    ordering = ['name']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return DeviceListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return DeviceCreateUpdateSerializer
        return DeviceDetailSerializer
    
    @action(detail=True, methods=['get'])
    def interfaces(self, request, pk=None):
        """Récupère toutes les interfaces du device"""
        device = self.get_object()
        interfaces = device.interfaces.all()
        serializer = InterfaceSerializer(interfaces, many=True)
        return success_response(serializer.data, "Interfaces retrieved")
    
    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        """Statistiques du device"""
        device = self.get_object()
        
        data = {
            'total_interfaces': device.interfaces.count(),
            'up_interfaces': device.interfaces.filter(status='up').count(),
            'down_interfaces': device.interfaces.filter(status='down').count(),
            'total_ip_addresses': IPAddress.objects.filter(interface__device=device).count(),
            'total_power_ports': device.power_ports.count(),
            'cpu_usage': device.cpu_usage,
            'memory_usage': device.memory_usage,
            'temperature': device.temperature,
            'uptime': device.uptime_display,
            'last_seen': device.last_seen,
            'is_reachable': device.is_reachable
        }
        
        return success_response(data, "Device statistics retrieved")
    
    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """Met à jour le statut du device"""
        device = self.get_object()
        
        device.status = request.data.get('status', device.status)
        device.cpu_usage = request.data.get('cpu_usage', device.cpu_usage)
        device.memory_usage = request.data.get('memory_usage', device.memory_usage)
        device.temperature = request.data.get('temperature', device.temperature)
        device.last_seen = timezone.now()
        device.save()
        
        serializer = DeviceDetailSerializer(device)
        return success_response(serializer.data, "Device status updated")
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Résumé global des devices"""
        total = Device.objects.count()
        by_status = Device.objects.values('status').annotate(count=Count('id'))
        by_type = Device.objects.values('device_type__device_class').annotate(count=Count('id'))
        by_site = Device.objects.values('site__name').annotate(count=Count('id'))
        
        online = Device.objects.filter(
            last_seen__gte=timezone.now() - timedelta(minutes=5)
        ).count()
        
        data = {
            'total': total,
            'online': online,
            'offline': total - online,
            'by_status': by_status,
            'by_type': by_type,
            'by_site': by_site
        }
        
        return success_response(data, "Device summary retrieved")
    
    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """Dashboard global des devices"""
        recent_devices = self.get_queryset().order_by('-created_at')[:10]
        critical_devices = self.get_queryset().filter(status='failed')
        
        data = {
            'recent_devices': DeviceListSerializer(recent_devices, many=True).data,
            'critical_devices': DeviceListSerializer(critical_devices, many=True).data,
            'statistics': {
                'total': Device.objects.count(),
                'active': Device.objects.filter(status='active').count(),
                'failed': Device.objects.filter(status='failed').count(),
                'maintenance': Device.objects.filter(status='maintenance').count()
            }
        }
        
        return success_response(data, "Device dashboard retrieved")


# ============================================================================
# INTERFACES
# ============================================================================

class InterfaceViewSet(viewsets.ModelViewSet):
    queryset = Interface.objects.select_related('device').prefetch_related('ip_addresses')
    serializer_class = InterfaceSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]  # Correction
    filterset_class = InterfaceFilter
    search_fields = ['name', 'description', 'mac_address']
    ordering_fields = ['name', 'status', 'created_at']
    ordering = ['device', 'name']
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return InterfaceDetailSerializer
        return InterfaceSerializer
    
    @action(detail=True, methods=['post'])
    def update_statistics(self, request, pk=None):
        """Met à jour les statistiques de l'interface"""
        interface = self.get_object()
        
        interface.rx_bytes = request.data.get('rx_bytes', interface.rx_bytes)
        interface.tx_bytes = request.data.get('tx_bytes', interface.tx_bytes)
        interface.rx_packets = request.data.get('rx_packets', interface.rx_packets)
        interface.tx_packets = request.data.get('tx_packets', interface.tx_packets)
        interface.rx_errors = request.data.get('rx_errors', interface.rx_errors)
        interface.tx_errors = request.data.get('tx_errors', interface.tx_errors)
        interface.save()
        
        return success_response(
            InterfaceSerializer(interface).data,
            "Interface statistics updated"
        )
    
    @action(detail=True, methods=['get'])
    def cables(self, request, pk=None):
        """Récupère les câbles connectés à l'interface"""
        interface = self.get_object()
        cables = list(interface.cables_a.all()) + list(interface.cables_b.all())
        serializer = CableSerializer(cables, many=True)
        return success_response(serializer.data, "Cables retrieved")


# ============================================================================
# IPAM
# ============================================================================

class VRFViewSet(viewsets.ModelViewSet):
    queryset = VRF.objects.prefetch_related('import_targets', 'export_targets')
    serializer_class = VRFSerializer
    permission_classes = [IsAuthenticated, CanManageInventory]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]  # Correction
    filterset_fields = ['tenant']
    search_fields = ['name', 'rd']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']


class RouteTargetViewSet(viewsets.ModelViewSet):
    queryset = RouteTarget.objects.all()
    serializer_class = RouteTargetSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination
    filter_backends = [drf_filters.SearchFilter, drf_filters.OrderingFilter]  # Correction
    search_fields = ['name']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']


class PrefixViewSet(viewsets.ModelViewSet):
    queryset = Prefix.objects.select_related('vrf', 'site', 'tenant')
    serializer_class = PrefixSerializer
    permission_classes = [IsAuthenticated, CanManageInventory]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]  # Correction
    filterset_class = PrefixFilter
    search_fields = ['prefix', 'description']
    ordering_fields = ['prefix', 'created_at', 'status']
    ordering = ['vrf', 'prefix']
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return PrefixDetailSerializer
        return PrefixSerializer
    
    @action(detail=True, methods=['get'])
    def available_ips(self, request, pk=None):
        """Récupère les IPs disponibles dans le préfixe"""
        prefix = self.get_object()
        available = prefix.get_available_ips()
        return success_response({
            'total': len(available),
            'ips': [str(ip) for ip in available[:100]]
        }, "Available IPs retrieved")
    
    @action(detail=True, methods=['get'])
    def available_prefixes(self, request, pk=None):
        """Récupère les sous-préfixes disponibles"""
        prefix = self.get_object()
        prefix_length = request.query_params.get('prefix_length', 24)
        
        try:
            prefix_length = int(prefix_length)
            available = prefix.get_available_prefixes(prefix_length)
            return success_response({
                'total': len(available),
                'prefixes': [str(p) for p in available]
            }, "Available prefixes retrieved")
        except ValueError:
            return error_response("Invalid prefix length")
    
    @action(detail=True, methods=['post'])
    def reserve_ip(self, request, pk=None):
        """Réserve une IP dans le préfixe"""
        prefix = self.get_object()
        
        ip = IPAMManager.reserve_ip(
            prefix=prefix,
            description=request.data.get('description', ''),
            dns_name=request.data.get('dns_name', '')
        )
        
        if ip:
            return created_response(
                IPAddressSerializer(ip).data,
                "IP reserved successfully"
            )
        return error_response("No IP available in this prefix")
    
    @action(detail=True, methods=['post'])
    def reserve_prefix(self, request, pk=None):
        """Réserve un sous-préfixe"""
        prefix = self.get_object()
        prefix_length = request.data.get('prefix_length')
        
        if not prefix_length:
            return error_response("prefix_length is required")
        
        try:
            prefix_length = int(prefix_length)
            new_prefix = IPAMManager.reserve_prefix(
                parent_prefix=prefix,
                prefix_length=prefix_length,
                description=request.data.get('description', '')
            )
            
            if new_prefix:
                return created_response(
                    PrefixSerializer(new_prefix).data,
                    "Prefix reserved successfully"
                )
            return error_response("No prefix available")
        except ValueError:
            return error_response("Invalid prefix length")


class IPAddressViewSet(viewsets.ModelViewSet):
    queryset = IPAddress.objects.select_related('vrf', 'interface', 'tenant')
    serializer_class = IPAddressSerializer
    permission_classes = [IsAuthenticated, CanManageInventory]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]  # Correction
    filterset_class = IPAddressFilter
    search_fields = ['address', 'dns_name', 'description']
    ordering_fields = ['address', 'created_at', 'status']
    ordering = ['vrf', 'address']


# ============================================================================
# VLANS
# ============================================================================

class VLANGroupViewSet(viewsets.ModelViewSet):
    queryset = VLANGroup.objects.select_related('site')
    serializer_class = VLANGroupSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]  # Correction
    filterset_fields = ['site']
    search_fields = ['name']
    ordering_fields = ['name', 'created_at']
    ordering = ['site', 'name']


class VLANViewSet(viewsets.ModelViewSet):
    queryset = VLAN.objects.select_related('site', 'group', 'tenant')
    serializer_class = VLANSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]  # Correction
    filterset_fields = ['site', 'group', 'status']
    search_fields = ['name', 'vlan_id']
    ordering_fields = ['vlan_id', 'name', 'created_at']
    ordering = ['site', 'vlan_id']


# ============================================================================
# CABLES
# ============================================================================

class CableViewSet(viewsets.ModelViewSet):
    queryset = Cable.objects.select_related(
        'interface_a__device', 'interface_b__device'
    )
    serializer_class = CableSerializer
    permission_classes = [IsAuthenticated, CanManageInventory]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]  # Correction
    filterset_fields = ['cable_type', 'status']
    search_fields = ['label', 'description']
    ordering_fields = ['created_at', 'length']
    ordering = ['-created_at']


class BreakoutCableViewSet(viewsets.ModelViewSet):
    queryset = BreakoutCable.objects.select_related('parent_cable', 'child_cable')
    serializer_class = BreakoutCableSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination
    filter_backends = [drf_filters.OrderingFilter]  # Correction
    ordering_fields = ['position', 'created_at']
    ordering = ['parent_cable', 'position']


# ============================================================================
# POWER
# ============================================================================

class PowerPortViewSet(viewsets.ModelViewSet):
    queryset = PowerPort.objects.select_related('device')
    serializer_class = PowerPortSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]  # Correction
    filterset_fields = ['device', 'port_type']
    search_fields = ['name']
    ordering_fields = ['name', 'allocated_power_w']
    ordering = ['device', 'name']


class PowerFeedViewSet(viewsets.ModelViewSet):
    queryset = PowerFeed.objects.select_related('power_port__device')
    serializer_class = PowerFeedSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, drf_filters.OrderingFilter]  # Correction
    filterset_fields = ['is_active']
    ordering_fields = ['voltage', 'power_w', 'last_measured']
    ordering = ['-last_measured']


# ============================================================================
# CIRCUITS
# ============================================================================

class ProviderViewSet(viewsets.ModelViewSet):
    queryset = Provider.objects.all()
    serializer_class = ProviderSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination
    filter_backends = [drf_filters.SearchFilter, drf_filters.OrderingFilter]  # Correction
    search_fields = ['name', 'account_number']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']


class CircuitViewSet(viewsets.ModelViewSet):
    queryset = Circuit.objects.select_related('provider', 'site_a', 'site_b', 'tenant')
    serializer_class = CircuitSerializer
    permission_classes = [IsAuthenticated, CanManageInventory]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]  # Correction
    filterset_fields = ['circuit_type', 'provider', 'status', 'site_a', 'site_b']
    search_fields = ['circuit_id']
    ordering_fields = ['circuit_id', 'bandwidth_mbps', 'created_at']
    ordering = ['provider', 'circuit_id']
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return CircuitDetailSerializer
        return CircuitSerializer


class CircuitTerminationViewSet(viewsets.ModelViewSet):
    queryset = CircuitTermination.objects.select_related('circuit', 'device', 'interface')
    serializer_class = CircuitTerminationSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, drf_filters.OrderingFilter]  # Correction
    filterset_fields = ['circuit', 'device', 'role']
    ordering_fields = ['created_at']
    ordering = ['circuit', 'role']


# ============================================================================
# ROUTING
# ============================================================================

class ASNViewSet(viewsets.ModelViewSet):
    queryset = ASN.objects.select_related('tenant')
    serializer_class = ASNSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]  # Correction
    filterset_fields = ['asn_type', 'tenant']
    search_fields = ['number', 'organization']
    ordering_fields = ['number', 'created_at']
    ordering = ['number']


class FHRPGroupViewSet(viewsets.ModelViewSet):
    queryset = FHRPGroup.objects.select_related('vlan')
    serializer_class = FHRPGroupSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, drf_filters.OrderingFilter]  # Correction
    filterset_fields = ['protocol', 'vlan']
    ordering_fields = ['group_id', 'priority', 'created_at']
    ordering = ['protocol', 'group_id']


class BGPSessionViewSet(viewsets.ModelViewSet):
    queryset = BGPSession.objects.select_related(
        'device_a', 'device_b', 'asn_a', 'asn_b', 'ip_a', 'ip_b'
    )
    serializer_class = BGPSessionSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]  # Correction
    filterset_fields = ['session_type', 'state', 'device_a', 'device_b']
    search_fields = ['name']
    ordering_fields = ['name', 'last_state_change', 'created_at']
    ordering = ['-created_at']


# ============================================================================
# VIRTUALISATION
# ============================================================================

class ClusterViewSet(viewsets.ModelViewSet):
    queryset = Cluster.objects.prefetch_related('hosts')
    serializer_class = ClusterSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]  # Correction
    filterset_fields = ['cluster_type', 'tenant']
    search_fields = ['name']
    ordering_fields = ['name', 'total_cpu_cores', 'total_ram_gb', 'created_at']
    ordering = ['name']
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ClusterDetailSerializer
        return ClusterSerializer


class VirtualMachineViewSet(viewsets.ModelViewSet):
    queryset = VirtualMachine.objects.select_related('cluster', 'host', 'tenant')
    serializer_class = VirtualMachineSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]  # Correction
    filterset_fields = ['cluster', 'host', 'power_state', 'tenant']
    search_fields = ['name', 'uuid']
    ordering_fields = ['name', 'vcpus', 'ram_gb', 'disk_gb', 'created_at']
    ordering = ['cluster', 'name']


# ============================================================================
# TENANCY
# ============================================================================

class TenantViewSet(viewsets.ModelViewSet):
    queryset = Tenant.objects.all()
    serializer_class = TenantSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination
    filter_backends = [drf_filters.SearchFilter, drf_filters.OrderingFilter]  # Correction
    search_fields = ['name', 'tenant_id']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']


class ContactViewSet(viewsets.ModelViewSet):
    queryset = Contact.objects.all()
    serializer_class = ContactSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination
    filter_backends = [drf_filters.SearchFilter, drf_filters.OrderingFilter]  # Correction
    search_fields = ['name', 'email']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']


class TenantAssignmentViewSet(viewsets.ModelViewSet):
    queryset = TenantAssignment.objects.select_related('tenant')
    serializer_class = TenantAssignmentSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, drf_filters.OrderingFilter]  # Correction
    filterset_fields = ['tenant', 'content_type']
    ordering_fields = ['created_at']
    ordering = ['-created_at']


# ============================================================================
# L2VPN
# ============================================================================

class L2VPNViewSet(viewsets.ModelViewSet):
    queryset = L2VPN.objects.select_related('tenant')
    serializer_class = L2VPNSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]  # Correction
    filterset_fields = ['vpn_type', 'tenant']
    search_fields = ['name']
    ordering_fields = ['name', 'vni', 'created_at']
    ordering = ['name']


# ============================================================================
# DASHBOARD & UTILITIES
# ============================================================================

class InventoryDashboardViewSet(viewsets.ViewSet):
    """Dashboard global de l'inventaire"""
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Résumé global de l'inventaire"""
        data = {
            'sites': Site.objects.count(),
            'racks': Rack.objects.count(),
            'devices': Device.objects.count(),
            'interfaces': Interface.objects.count(),
            'ip_addresses': IPAddress.objects.count(),
            'vlans': VLAN.objects.count(),
            'cables': Cable.objects.count(),
            'circuits': Circuit.objects.count(),
            'clusters': Cluster.objects.count(),
            'virtual_machines': VirtualMachine.objects.count(),
            'tenants': Tenant.objects.count(),
        }
        return success_response(data, "Inventory summary retrieved")
    
    @action(detail=False, methods=['get'])
    def charts(self, request):
        """Données pour les graphiques"""
        # Devices by status
        devices_by_status = Device.objects.values('status').annotate(
            count=Count('id')
        )
        
        # Devices by type
        devices_by_type = Device.objects.values('device_type__device_class').annotate(
            count=Count('id')
        )
        
        # IP usage by VRF
        ips_by_vrf = VRF.objects.annotate(
            total_ips=Count('ip_addresses'),
            used_ips=Count('ip_addresses', filter=Q(ip_addresses__status='active'))
        ).values('name', 'total_ips', 'used_ips')
        
        data = {
            'devices_by_status': devices_by_status,
            'devices_by_type': devices_by_type,
            'ips_by_vrf': ips_by_vrf,
            'sites_by_region': Site.objects.values('region__name').annotate(count=Count('id')),
        }
        
        return success_response(data, "Chart data retrieved")