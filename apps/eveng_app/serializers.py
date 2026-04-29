"""
EVE-NG App Serializers - API serializers professionnels
"""
from rest_framework import serializers
from django.utils import timezone
from .models import (
    EVENServer, EVENLab, EVENNode, EVENNetwork,
    EVENLink, EVENImage, EVENUserSession
)


# ============================================================================
# SERVEURS EVE-NG
# ============================================================================

class EVENServerSerializer(serializers.ModelSerializer):
    """Serializer de base pour les serveurs EVE-NG"""
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True, allow_null=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    labs_count = serializers.IntegerField(source='labs.count', read_only=True)
    images_count = serializers.IntegerField(source='images.count', read_only=True)
    
    class Meta:
        model = EVENServer
        fields = [
            'id', 'name', 'description', 'url', 'username', 'password',
            'timeout', 'status', 'status_display', 'version',
            'cpu_usage', 'memory_usage', 'disk_usage', 'last_sync_at',
            'labs_count', 'images_count', 'created_by', 'created_by_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by',
                           'version', 'last_sync_at', 'labs_count', 'images_count',
                           'cpu_usage', 'memory_usage', 'disk_usage']
        extra_kwargs = {
            'password': {'write_only': True},
        }


class EVENServerDetailSerializer(EVENServerSerializer):
    """Serializer détaillé pour les serveurs EVE-NG"""
    labs = serializers.SerializerMethodField()
    images = serializers.SerializerMethodField()
    sessions = serializers.SerializerMethodField()
    
    class Meta(EVENServerSerializer.Meta):
        fields = EVENServerSerializer.Meta.fields + ['labs', 'images', 'sessions']
    
    def get_labs(self, obj):
        labs = obj.labs.all()[:10]
        return [{
            'id': str(l.id),
            'name': l.name,
            'lab_path': l.lab_path,
            'status': l.get_status_display(),
            'node_count': l.node_count,
            'is_active': l.is_active
        } for l in labs]
    
    def get_images(self, obj):
        images = obj.images.all()[:10]
        return [{
            'id': str(i.id),
            'name': i.name,
            'image_type': i.get_image_type_display(),
            'version': i.version,
            'size_mb': i.size_mb
        } for i in images]
    
    def get_sessions(self, obj):
        sessions = obj.sessions.filter(is_active=True)[:5]
        return [{
            'id': str(s.id),
            'user_email': s.user.email,
            'last_activity_at': s.last_activity_at
        } for s in sessions]


# ============================================================================
# LABORATOIRES EVE-NG
# ============================================================================

class EVENLabSerializer(serializers.ModelSerializer):
    """Serializer pour les laboratoires EVE-NG"""
    server_name = serializers.CharField(source='server.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True, allow_null=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = EVENLab
        fields = [
            'id', 'server', 'server_name', 'lab_path', 'name', 'description',
            'lab_id', 'filename', 'folder', 'status', 'status_display',
            'node_count', 'link_count', 'network_count', 'config', 'topology',
            'synced_at', 'is_active', 'created_by', 'created_by_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'synced_at',
                           'node_count', 'link_count', 'network_count']


class EVENLabDetailSerializer(EVENLabSerializer):
    """Serializer détaillé pour les laboratoires"""
    nodes = serializers.SerializerMethodField()
    networks = serializers.SerializerMethodField()
    links = serializers.SerializerMethodField()
    
    class Meta(EVENLabSerializer.Meta):
        fields = EVENLabSerializer.Meta.fields + ['nodes', 'networks', 'links']
    
    def get_nodes(self, obj):
        nodes = obj.nodes.all().order_by('node_id')
        return [{
            'id': str(n.id),
            'node_id': n.node_id,
            'name': n.name,
            'node_type': n.get_node_type_display(),
            'status': n.get_status_display(),
            'cpu': n.cpu,
            'ram': n.ram,
            'console_port': n.console_port,
            'position_x': n.position_x,
            'position_y': n.position_y
        } for n in nodes]
    
    def get_networks(self, obj):
        networks = obj.networks.all()
        return [{
            'id': str(n.id),
            'network_id': n.network_id,
            'name': n.name,
            'network_type': n.get_network_type_display()
        } for n in networks]
    
    def get_links(self, obj):
        links = obj.links.all()
        return [{
            'id': str(l.id),
            'source_node': l.source_node.name,
            'destination_node': l.destination_node.name,
            'link_type': l.get_link_type_display()
        } for l in links]


# ============================================================================
# NŒUDS EVE-NG
# ============================================================================

class EVENNodeSerializer(serializers.ModelSerializer):
    """Serializer pour les nœuds EVE-NG"""
    lab_name = serializers.CharField(source='lab.name', read_only=True)
    server_name = serializers.CharField(source='lab.server.name', read_only=True)
    node_type_display = serializers.CharField(source='get_node_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    console_type_display = serializers.CharField(source='get_console_type_display', read_only=True)
    
    class Meta:
        model = EVENNode
        fields = [
            'id', 'lab', 'lab_name', 'server_name', 'node_id', 'name',
            'node_type', 'node_type_display', 'image', 'template',
            'status', 'status_display', 'cpu', 'ram', 'ethernet',
            'console', 'console_type', 'console_type_display', 'console_port',
            'position_x', 'position_y', 'config', 'interfaces', 'url',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


# ============================================================================
# RÉSEAUX EVE-NG
# ============================================================================

class EVENNetworkSerializer(serializers.ModelSerializer):
    """Serializer pour les réseaux EVE-NG"""
    lab_name = serializers.CharField(source='lab.name', read_only=True)
    server_name = serializers.CharField(source='lab.server.name', read_only=True)
    network_type_display = serializers.CharField(source='get_network_type_display', read_only=True)
    
    class Meta:
        model = EVENNetwork
        fields = [
            'id', 'lab', 'lab_name', 'server_name', 'network_id', 'name',
            'network_type', 'network_type_display', 'left', 'top', 'count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


# ============================================================================
# LIENS EVE-NG
# ============================================================================

class EVENLinkSerializer(serializers.ModelSerializer):
    """Serializer pour les liens EVE-NG"""
    lab_name = serializers.CharField(source='lab.name', read_only=True)
    server_name = serializers.CharField(source='lab.server.name', read_only=True)
    source_node_name = serializers.CharField(source='source_node.name', read_only=True)
    destination_node_name = serializers.CharField(source='destination_node.name', read_only=True)
    link_type_display = serializers.CharField(source='get_link_type_display', read_only=True)
    
    class Meta:
        model = EVENLink
        fields = [
            'id', 'lab', 'lab_name', 'server_name',
            'source_node', 'source_node_name', 'source_label', 'source_interface',
            'destination_node', 'destination_node_name', 'destination_label', 'destination_interface',
            'link_type', 'link_type_display', 'color', 'width',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


# ============================================================================
# IMAGES EVE-NG
# ============================================================================

class EVENImageSerializer(serializers.ModelSerializer):
    """Serializer pour les images EVE-NG"""
    server_name = serializers.CharField(source='server.name', read_only=True)
    image_type_display = serializers.CharField(source='get_image_type_display', read_only=True)
    
    class Meta:
        model = EVENImage
        fields = [
            'id', 'server', 'server_name', 'name', 'image_type',
            'image_type_display', 'path', 'description', 'version',
            'size_mb', 'default_cpu', 'default_ram', 'default_ethernet',
            'synced_at', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'synced_at', 'size_mb']


# ============================================================================
# SESSIONS UTILISATEURS
# ============================================================================

class EVENUserSessionSerializer(serializers.ModelSerializer):
    """Serializer pour les sessions utilisateurs"""
    server_name = serializers.CharField(source='server.name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    
    class Meta:
        model = EVENUserSession
        fields = [
            'id', 'server', 'server_name', 'user', 'user_email',
            'session_id', 'cookie', 'logged_in_at', 'last_activity_at',
            'expires_at', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'logged_in_at',
                           'last_activity_at', 'session_id']
        extra_kwargs = {
            'cookie': {'write_only': True},
        }


# ============================================================================
# REQUESTS
# ============================================================================

class EVENLabStartStopSerializer(serializers.Serializer):
    """Serializer pour démarrer/arrêter un lab"""
    lab_path = serializers.CharField(required=True)
    wait = serializers.BooleanField(default=False)


class EVENNodeStartStopSerializer(serializers.Serializer):
    """Serializer pour démarrer/arrêter un nœud"""
    lab_path = serializers.CharField(required=True)
    node_id = serializers.IntegerField(required=True)


# ============================================================================
# DASHBOARD
# ============================================================================

class EVENDashboardStatsSerializer(serializers.Serializer):
    """Serializer pour les statistiques du dashboard"""
    total_servers = serializers.IntegerField()
    active_servers = serializers.IntegerField()
    total_labs = serializers.IntegerField()
    running_labs = serializers.IntegerField()
    total_nodes = serializers.IntegerField()
    running_nodes = serializers.IntegerField()
    total_images = serializers.IntegerField()
    active_sessions = serializers.IntegerField()


class EVENRecentLabSerializer(serializers.Serializer):
    """Serializer pour les laboratoires récents"""
    id = serializers.UUIDField()
    name = serializers.CharField()
    server_name = serializers.CharField()
    status = serializers.CharField()
    node_count = serializers.IntegerField()
    updated_at = serializers.DateTimeField()


class EVENDashboardSerializer(serializers.Serializer):
    """Serializer pour le dashboard EVE-NG"""
    statistics = EVENDashboardStatsSerializer()
    recent_labs = EVENRecentLabSerializer(many=True)
    labs_by_status = serializers.ListField(child=serializers.DictField())
    nodes_by_type = serializers.ListField(child=serializers.DictField())
    top_images = serializers.ListField(child=serializers.DictField())