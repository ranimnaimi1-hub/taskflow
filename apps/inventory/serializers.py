# apps/inventory/serializers.py
"""
Inventory Serializers - Ultra Professional
Sérialiseurs pour tous les modèles
"""
from rest_framework import serializers
from .models import *


# ============================================================================
# HIÉRARCHIE
# ============================================================================

class RegionSerializer(serializers.ModelSerializer):
    sites_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Region
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_sites_count(self, obj):
        return obj.sites.count()


class SiteSerializer(serializers.ModelSerializer):
    region_name = serializers.CharField(source='region.name', read_only=True)
    parent_name = serializers.CharField(source='parent.name', read_only=True)
    devices_count = serializers.SerializerMethodField()
    racks_count = serializers.SerializerMethodField()
    vlans_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Site
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_devices_count(self, obj):
        return obj.devices.count()
    
    def get_racks_count(self, obj):
        return obj.racks.count()
    
    def get_vlans_count(self, obj):
        return obj.vlans.count()


class LocationSerializer(serializers.ModelSerializer):
    site_name = serializers.CharField(source='site.name', read_only=True)
    racks_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Location
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_racks_count(self, obj):
        return obj.racks.count()


# ============================================================================
# MANUFACTURERS ET DEVICE TYPES
# ============================================================================

class ManufacturerSerializer(serializers.ModelSerializer):
    device_types_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Manufacturer
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_device_types_count(self, obj):
        return obj.device_types.count()


class DeviceTypeSerializer(serializers.ModelSerializer):
    manufacturer_name = serializers.CharField(source='manufacturer.name', read_only=True)
    
    class Meta:
        model = DeviceType
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


# ============================================================================
# RACKS
# ============================================================================

class RackSerializer(serializers.ModelSerializer):
    site_name = serializers.CharField(source='site.name', read_only=True)
    location_name = serializers.CharField(source='location.name', read_only=True)
    devices_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Rack
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_devices_count(self, obj):
        return obj.devices.count()


class RackDetailSerializer(RackSerializer):
    devices = serializers.SerializerMethodField()
    
    def get_devices(self, obj):
        devices = obj.devices.all()
        return DeviceListSerializer(devices, many=True).data


# ============================================================================
# IPAM
# ============================================================================
class VRFSerializer(serializers.ModelSerializer):
    tenant_name = serializers.CharField(source='tenant.name', read_only=True)
    prefixes_count = serializers.SerializerMethodField()
    import_targets_details = serializers.StringRelatedField(many=True, read_only=True)
    export_targets_details = serializers.StringRelatedField(many=True, read_only=True)
    
    class Meta:
        model = VRF
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_prefixes_count(self, obj):
        return obj.prefixes.count()


class RouteTargetSerializer(serializers.ModelSerializer):
    tenant_name = serializers.CharField(source='tenant.name', read_only=True)
    
    class Meta:
        model = RouteTarget
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class PrefixSerializer(serializers.ModelSerializer):
    vrf_name = serializers.CharField(source='vrf.name', read_only=True)
    site_name = serializers.CharField(source='site.name', read_only=True)
    tenant_name = serializers.CharField(source='tenant.name', read_only=True)
    available_ips = serializers.SerializerMethodField()
    
    class Meta:
        model = Prefix
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'family']
    
    def get_available_ips(self, obj):
        return len(obj.get_available_ips()) if obj.is_pool else 0


class PrefixDetailSerializer(PrefixSerializer):
    child_prefixes = serializers.SerializerMethodField()
    ip_addresses = serializers.SerializerMethodField()
    
    def get_child_prefixes(self, obj):
        children = Prefix.objects.filter(prefix__startswith=obj.prefix).exclude(id=obj.id)
        return PrefixSerializer(children, many=True).data
    
    def get_ip_addresses(self, obj):
        ips = IPAddress.objects.filter(address__startswith=obj.prefix.split('/')[0])
        return IPAddressSerializer(ips, many=True).data


class IPAddressSerializer(serializers.ModelSerializer):
    vrf_name = serializers.CharField(source='vrf.name', read_only=True)
    interface_name = serializers.CharField(source='interface.name', read_only=True)
    device_name = serializers.CharField(source='interface.device.name', read_only=True)
    tenant_name = serializers.CharField(source='tenant.name', read_only=True)
    family_display = serializers.CharField(source='get_family_display', read_only=True)
    
    class Meta:
        model = IPAddress
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'family']
    
    def validate(self, data):
        """Vérifie que l'adresse IP est unique dans le VRF"""
        vrf = data.get('vrf')
        address = data.get('address')
        if vrf and address:
            if IPAddress.objects.filter(vrf=vrf, address=address).exists():
                raise serializers.ValidationError(
                    f"IP address {address} already exists in VRF {vrf.name}"
                )
        return data


# ============================================================================
# VLANs
# ============================================================================

class VLANGroupSerializer(serializers.ModelSerializer):
    site_name = serializers.CharField(source='site.name', read_only=True)
    vlans_count = serializers.SerializerMethodField()
    
    class Meta:
        model = VLANGroup
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_vlans_count(self, obj):
        return obj.vlans.count()


class VLANSerializer(serializers.ModelSerializer):
    site_name = serializers.CharField(source='site.name', read_only=True)
    group_name = serializers.CharField(source='group.name', read_only=True)
    tenant_name = serializers.CharField(source='tenant.name', read_only=True)
    
    class Meta:
        model = VLAN
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


# ============================================================================
# INTERFACES
# ============================================================================

class InterfaceSerializer(serializers.ModelSerializer):
    device_name = serializers.CharField(source='device.name', read_only=True)
    device_hostname = serializers.CharField(source='device.hostname', read_only=True)
    ip_addresses = IPAddressSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Interface
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class InterfaceDetailSerializer(InterfaceSerializer):
    cables_a = serializers.SerializerMethodField()
    cables_b = serializers.SerializerMethodField()
    
    def get_cables_a(self, obj):
        cables = obj.cables_a.all()
        return CableSerializer(cables, many=True).data
    
    def get_cables_b(self, obj):
        cables = obj.cables_b.all()
        return CableSerializer(cables, many=True).data


# ============================================================================
# CABLES
# ============================================================================

class CableSerializer(serializers.ModelSerializer):
    interface_a_info = serializers.SerializerMethodField()
    interface_b_info = serializers.SerializerMethodField()
    
    class Meta:
        model = Cable
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_interface_a_info(self, obj):
        return {
            'id': obj.interface_a.id,
            'device': obj.interface_a.device.name,
            'interface': obj.interface_a.name,
            'device_id': obj.interface_a.device.id
        }
    
    def get_interface_b_info(self, obj):
        return {
            'id': obj.interface_b.id,
            'device': obj.interface_b.device.name,
            'interface': obj.interface_b.name,
            'device_id': obj.interface_b.device.id
        }


class BreakoutCableSerializer(serializers.ModelSerializer):
    parent_cable_info = serializers.SerializerMethodField()
    child_cable_info = serializers.SerializerMethodField()
    
    class Meta:
        model = BreakoutCable
        fields = '__all__'
    
    def get_parent_cable_info(self, obj):
        return {
            'id': obj.parent_cable.id,
            'type': obj.parent_cable.cable_type,
            'interface_a': str(obj.parent_cable.interface_a),
            'interface_b': str(obj.parent_cable.interface_b)
        }
    
    def get_child_cable_info(self, obj):
        return {
            'id': obj.child_cable.id,
            'type': obj.child_cable.cable_type,
            'interface_a': str(obj.child_cable.interface_a),
            'interface_b': str(obj.child_cable.interface_b)
        }


# ============================================================================
# POWER
# ============================================================================

class PowerPortSerializer(serializers.ModelSerializer):
    device_name = serializers.CharField(source='device.name', read_only=True)
    feeds_count = serializers.SerializerMethodField()
    
    class Meta:
        model = PowerPort
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_feeds_count(self, obj):
        return obj.feeds.count()


class PowerFeedSerializer(serializers.ModelSerializer):
    power_port_name = serializers.CharField(source='power_port.name', read_only=True)
    device_name = serializers.CharField(source='power_port.device.name', read_only=True)
    
    class Meta:
        model = PowerFeed
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


# ============================================================================
# DEVICES
# ============================================================================

class DeviceListSerializer(serializers.ModelSerializer):
    site_name = serializers.CharField(source='site.name', read_only=True)
    device_type_name = serializers.CharField(source='device_type.name', read_only=True)
    manufacturer_name = serializers.CharField(source='device_type.manufacturer.name', read_only=True)
    rack_name = serializers.CharField(source='rack.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_reachable = serializers.BooleanField(read_only=True)
    uptime = serializers.CharField(source='uptime_display', read_only=True)
    
    class Meta:
        model = Device
        fields = [
            'id', 'name', 'hostname', 'device_type_name', 'manufacturer_name',
            'site_name', 'rack_name', 'rack_position', 'management_ip',
            'status', 'status_display', 'role', 'is_reachable', 'uptime',
            'last_seen', 'cpu_usage', 'memory_usage', 'created_at'
        ]


class DeviceDetailSerializer(serializers.ModelSerializer):
    site = SiteSerializer(read_only=True)
    device_type = DeviceTypeSerializer(read_only=True)
    rack = RackSerializer(read_only=True)
    tenant = serializers.StringRelatedField(read_only=True)
    owner = serializers.StringRelatedField(read_only=True)
    interfaces = InterfaceSerializer(many=True, read_only=True)
    power_ports = PowerPortSerializer(many=True, read_only=True)
    bgp_sessions_a = serializers.SerializerMethodField()
    bgp_sessions_b = serializers.SerializerMethodField()
    circuit_terminations = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    uptime = serializers.CharField(source='uptime_display', read_only=True)
    is_reachable = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Device
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_bgp_sessions_a(self, obj):
        sessions = obj.bgp_sessions_a.all()
        return BGPSessionSerializer(sessions, many=True).data
    
    def get_bgp_sessions_b(self, obj):
        sessions = obj.bgp_sessions_b.all()
        return BGPSessionSerializer(sessions, many=True).data
    
    def get_circuit_terminations(self, obj):
        terms = obj.circuit_terminations.all()
        return CircuitTerminationSerializer(terms, many=True).data


class DeviceCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = '__all__'
    
    def validate_management_ip(self, value):
        """Vérifie que l'IP de management est unique"""
        if Device.objects.filter(management_ip=value).exclude(id=self.instance.id if self.instance else None).exists():
            raise serializers.ValidationError("This management IP is already in use.")
        return value


# ============================================================================
# CIRCUITS
# ============================================================================

class ProviderSerializer(serializers.ModelSerializer):
    circuits_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Provider
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_circuits_count(self, obj):
        return obj.circuits.count()


class CircuitSerializer(serializers.ModelSerializer):
    provider_name = serializers.CharField(source='provider.name', read_only=True)
    site_a_name = serializers.CharField(source='site_a.name', read_only=True)
    site_b_name = serializers.CharField(source='site_b.name', read_only=True)
    tenant_name = serializers.CharField(source='tenant.name', read_only=True)
    
    class Meta:
        model = Circuit
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class CircuitDetailSerializer(CircuitSerializer):
    terminations = serializers.SerializerMethodField()
    
    def get_terminations(self, obj):
        terms = obj.terminations.all()
        return CircuitTerminationSerializer(terms, many=True).data


class CircuitTerminationSerializer(serializers.ModelSerializer):
    circuit_id = serializers.CharField(source='circuit.circuit_id', read_only=True)
    device_name = serializers.CharField(source='device.name', read_only=True)
    interface_name = serializers.CharField(source='interface.name', read_only=True)
    
    class Meta:
        model = CircuitTermination
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


# ============================================================================
# ROUTING
# ============================================================================

class ASNSerializer(serializers.ModelSerializer):
    tenant_name = serializers.CharField(source='tenant.name', read_only=True)
    
    class Meta:
        model = ASN
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class FHRPGroupSerializer(serializers.ModelSerializer):
    vlan_name = serializers.CharField(source='vlan.name', read_only=True)
    
    class Meta:
        model = FHRPGroup
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class BGPSessionSerializer(serializers.ModelSerializer):
    device_a_name = serializers.CharField(source='device_a.name', read_only=True)
    device_b_name = serializers.CharField(source='device_b.name', read_only=True)
    asn_a_number = serializers.CharField(source='asn_a.number', read_only=True)
    asn_b_number = serializers.CharField(source='asn_b.number', read_only=True)
    ip_a_address = serializers.CharField(source='ip_a.address', read_only=True)
    ip_b_address = serializers.CharField(source='ip_b.address', read_only=True)
    
    class Meta:
        model = BGPSession
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


# ============================================================================
# VIRTUALISATION
# ============================================================================

class ClusterSerializer(serializers.ModelSerializer):
    tenant_name = serializers.CharField(source='tenant.name', read_only=True)
    hosts_count = serializers.SerializerMethodField()
    vms_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Cluster
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_hosts_count(self, obj):
        return obj.hosts.count()
    
    def get_vms_count(self, obj):
        return obj.vms.count()


class ClusterDetailSerializer(ClusterSerializer):
    hosts = DeviceListSerializer(many=True, read_only=True)
    vms = serializers.SerializerMethodField()
    
    def get_vms(self, obj):
        vms = obj.vms.all()
        return VirtualMachineSerializer(vms, many=True).data


class VirtualMachineSerializer(serializers.ModelSerializer):
    cluster_name = serializers.CharField(source='cluster.name', read_only=True)
    host_name = serializers.CharField(source='host.name', read_only=True)
    tenant_name = serializers.CharField(source='tenant.name', read_only=True)
    interfaces = InterfaceSerializer(many=True, read_only=True)
    ip_addresses = IPAddressSerializer(many=True, read_only=True)
    
    class Meta:
        model = VirtualMachine
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


# ============================================================================
# TENANCY
# ============================================================================

class TenantSerializer(serializers.ModelSerializer):
    parent_name = serializers.CharField(source='parent.name', read_only=True)
    devices_count = serializers.SerializerMethodField()
    vlans_count = serializers.SerializerMethodField()
    prefixes_count = serializers.SerializerMethodField()
    vrfs_count = serializers.SerializerMethodField()
    circuits_count = serializers.SerializerMethodField()
    clusters_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Tenant
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_devices_count(self, obj):
        return obj.devices.count()
    
    def get_vlans_count(self, obj):
        return obj.vlans.count()
    
    def get_prefixes_count(self, obj):
        return obj.prefixes.count()
    
    def get_vrfs_count(self, obj):
        return obj.vrfs.count()
    
    def get_circuits_count(self, obj):
        return obj.circuits.count()
    
    def get_clusters_count(self, obj):
        return obj.clusters.count()


class ContactSerializer(serializers.ModelSerializer):
    tenants = serializers.StringRelatedField(many=True, read_only=True)
    sites = serializers.StringRelatedField(many=True, read_only=True)
    
    class Meta:
        model = Contact
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class TenantAssignmentSerializer(serializers.ModelSerializer):
    tenant_name = serializers.CharField(source='tenant.name', read_only=True)
    content_type_name = serializers.CharField(source='content_type.model', read_only=True)
    
    class Meta:
        model = TenantAssignment
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


# ============================================================================
# L2VPN
# ============================================================================

class L2VPNSerializer(serializers.ModelSerializer):
    tenant_name = serializers.CharField(source='tenant.name', read_only=True)
    
    class Meta:
        model = L2VPN
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']