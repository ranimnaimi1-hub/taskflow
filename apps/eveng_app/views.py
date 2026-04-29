"""
EVE-NG App Views - API endpoints professionnels
"""
from rest_framework import viewsets, status
from rest_framework import filters as drf_filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count, Q, Avg
from django.utils import timezone
from datetime import timedelta
import logging

from apps.core.permissions import IsActiveUser, HasAPIAccess
from apps.core.pagination import StandardPagination
from apps.core.responses import success_response, created_response, error_response

from .models import (
    EVENServer, EVENLab, EVENNode, EVENNetwork,
    EVENLink, EVENImage, EVENUserSession
)
from .serializers import (
    EVENServerSerializer, EVENServerDetailSerializer,
    EVENLabSerializer, EVENLabDetailSerializer,
    EVENNodeSerializer,
    EVENNetworkSerializer,
    EVENLinkSerializer,
    EVENImageSerializer,
    EVENUserSessionSerializer,
    EVENLabStartStopSerializer,
    EVENNodeStartStopSerializer
)
from .filters import (
    EVENServerFilter,
    EVENLabFilter,
    EVENNodeFilter,
    EVENNetworkFilter,
    EVENLinkFilter,
    EVENImageFilter,
    EVENUserSessionFilter
)
from .eveng_client import EVENGClient

logger = logging.getLogger(__name__)


# ============================================================================
# SERVEURS EVE-NG
# ============================================================================

class EVENServerViewSet(viewsets.ModelViewSet):
    """ViewSet pour les serveurs EVE-NG"""
    
    queryset = EVENServer.objects.select_related('created_by').prefetch_related(
        'labs', 'images', 'sessions'
    ).all()
    
    serializer_class = EVENServerSerializer
    serializer_classes = {
        'retrieve': EVENServerDetailSerializer,
        'default': EVENServerSerializer
    }
    
    permission_classes = [IsAuthenticated, IsActiveUser, HasAPIAccess]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_class = EVENServerFilter
    search_fields = ['name', 'description', 'url']
    ordering_fields = ['name', 'created_at', 'last_sync_at']
    ordering = ['name']
    
    def get_serializer_class(self):
        return self.serializer_classes.get(self.action, self.serializer_classes['default'])
    
    def get_queryset(self):
        user = self.request.user
        
        if not user or not user.is_authenticated:
            return EVENServer.objects.none()
        
        if hasattr(user, 'role') and user.role in ['superadmin', 'admin']:
            return EVENServer.objects.all()
        
        return EVENServer.objects.filter(created_by=user)
    
    def perform_create(self, serializer):
        if self.request.user.is_authenticated:
            serializer.save(created_by=self.request.user)
        else:
            serializer.save()
    
    @action(detail=True, methods=['post'])
    def sync(self, request, pk=None):
        """Synchronise toutes les données du serveur EVE-NG"""
        server = self.get_object()
        
        if not self._can_access_object(server):
            self.permission_denied(request)
        
        client = server.get_client()
        
        # Login
        login_result = client.login()
        if not login_result['success']:
            return error_response("Cannot login to EVE-NG server", login_result)
        
        # Récupérer le statut système
        status_result = client.get_system_status()
        if status_result['success']:
            status_data = status_result.get('status', {})
            server.version = status_data.get('version', '')
            server.cpu_usage = status_data.get('cpu', 0)
            server.memory_usage = status_data.get('memory', 0)
            server.disk_usage = status_data.get('disk', 0)
        
        server.last_sync_at = timezone.now()
        server.save()
        
        # Synchroniser les labs
        self._sync_labs(server, client)
        
        return success_response(
            EVENServerDetailSerializer(server).data,
            "Server synchronized successfully"
        )
    
    @action(detail=True, methods=['get'])
    def login_test(self, request, pk=None):
        """Teste la connexion au serveur EVE-NG"""
        server = self.get_object()
        
        if not self._can_access_object(server):
            self.permission_denied(request)
        
        client = server.get_client()
        result = client.login()
        
        if result['success']:
            # Créer une session
            session = EVENUserSession.objects.create(
                server=server,
                user=request.user,
                session_id=result.get('session_id', ''),
                cookie=client.session.cookies.get('unetlab_session', ''),
                expires_at=timezone.now() + timedelta(hours=8),
                is_active=True
            )
            
            return success_response(
                {'message': 'Login successful', 'session_id': str(session.id)},
                "Login successful"
            )
        
        return error_response("Login failed", result)
    
    @action(detail=True, methods=['get'])
    def labs(self, request, pk=None):
        """Liste tous les labs du serveur"""
        server = self.get_object()
        
        if not self._can_access_object(server):
            self.permission_denied(request)
        
        labs = server.labs.all()
        page = self.paginate_queryset(labs)
        
        if page is not None:
            serializer = EVENLabSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = EVENLabSerializer(labs, many=True)
        return success_response(serializer.data, "Labs retrieved")
    
    @action(detail=True, methods=['get'])
    def images(self, request, pk=None):
        """Liste toutes les images du serveur"""
        server = self.get_object()
        
        if not self._can_access_object(server):
            self.permission_denied(request)
        
        images = server.images.all()
        page = self.paginate_queryset(images)
        
        if page is not None:
            serializer = EVENImageSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = EVENImageSerializer(images, many=True)
        return success_response(serializer.data, "Images retrieved")
    
    def _sync_labs(self, server, client):
        """Synchronise les laboratoires"""
        result = client.get_labs()
        if not result['success']:
            return
        
        labs_data = result.get('labs', {})
        
        for lab_path, lab_info in labs_data.items():
            lab, created = EVENLab.objects.update_or_create(
                server=server,
                lab_path=lab_path,
                defaults={
                    'name': lab_info.get('name', lab_path.split('/')[-1]),
                    'description': lab_info.get('description', ''),
                    'lab_id': lab_info.get('id', ''),
                    'filename': lab_info.get('filename', ''),
                    'folder': '/'.join(lab_path.split('/')[:-1]) if '/' in lab_path else '',
                    'synced_at': timezone.now(),
                    'is_active': True
                }
            )
            
            # Récupérer les détails du lab
            self._sync_lab_details(lab, client)
    
    def _sync_lab_details(self, lab, client):
        """Synchronise les détails d'un laboratoire"""
        result = client.get_lab(lab.lab_path)
        if not result['success']:
            return
        
        lab_data = result.get('lab', {})
        
        # Mettre à jour les compteurs
        nodes = lab_data.get('nodes', {})
        networks = lab_data.get('networks', {})
        
        lab.node_count = len(nodes)
        lab.network_count = len(networks)
        lab.config = lab_data.get('config', {})
        lab.topology = lab_data.get('topology', {})
        lab.save()
        
        # Synchroniser les nœuds
        self._sync_nodes(lab, nodes, client)
        
        # Synchroniser les réseaux
        self._sync_networks(lab, networks)
    
    def _sync_nodes(self, lab, nodes_data, client):
        """Synchronise les nœuds d'un laboratoire"""
        for node_id, node_info in nodes_data.items():
            node, created = EVENNode.objects.update_or_create(
                lab=lab,
                node_id=int(node_id),
                defaults={
                    'name': node_info.get('name', f'Node {node_id}'),
                    'node_type': self._map_node_type(node_info.get('type', '')),
                    'image': node_info.get('image', ''),
                    'template': node_info.get('template', ''),
                    'cpu': node_info.get('cpu', 1),
                    'ram': node_info.get('ram', 512),
                    'ethernet': node_info.get('ethernet', 4),
                    'console': node_info.get('console', ''),
                    'console_port': node_info.get('console_port'),
                    'position_x': node_info.get('x', 0),
                    'position_y': node_info.get('y', 0),
                    'config': node_info.get('config', {}),
                    'interfaces': node_info.get('interfaces', []),
                    'url': node_info.get('url', ''),
                }
            )
    
    def _sync_networks(self, lab, networks_data):
        """Synchronise les réseaux d'un laboratoire"""
        for network_id, network_info in networks_data.items():
            network, created = EVENNetwork.objects.update_or_create(
                lab=lab,
                network_id=int(network_id),
                defaults={
                    'name': network_info.get('name', ''),
                    'network_type': network_info.get('type', 'bridge'),
                    'left': network_info.get('left', 0),
                    'top': network_info.get('top', 0),
                    'count': network_info.get('count', 0),
                }
            )
    
    def _map_node_type(self, node_type):
        """Convertit le type de nœud EVE-NG en type interne"""
        type_mapping = {
            'router': 'router',
            'switch': 'switch',
            'firewall': 'firewall',
            'host': 'host',
            'server': 'server',
            'vm': 'vm',
            'docker': 'docker',
        }
        return type_mapping.get(node_type.lower(), 'other')
    
    def _can_access_object(self, obj):
        user = self.request.user
        if not user or not user.is_authenticated:
            return False
        
        if hasattr(user, 'role') and user.role in ['superadmin', 'admin']:
            return True
        
        return obj.created_by == user


# ============================================================================
# LABORATOIRES EVE-NG
# ============================================================================

class EVENLabViewSet(viewsets.ModelViewSet):
    """ViewSet pour les laboratoires EVE-NG"""
    
    queryset = EVENLab.objects.select_related('server', 'created_by').prefetch_related(
        'nodes', 'networks', 'links'
    ).all()
    
    serializer_class = EVENLabSerializer
    serializer_classes = {
        'retrieve': EVENLabDetailSerializer,
        'default': EVENLabSerializer
    }
    
    permission_classes = [IsAuthenticated, IsActiveUser, HasAPIAccess]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_class = EVENLabFilter
    search_fields = ['name', 'description', 'lab_path']
    ordering_fields = ['name', 'created_at', 'updated_at']
    ordering = ['name']
    
    def get_serializer_class(self):
        return self.serializer_classes.get(self.action, self.serializer_classes['default'])
    
    def get_queryset(self):
        user = self.request.user
        
        if not user or not user.is_authenticated:
            return EVENLab.objects.none()
        
        if hasattr(user, 'role') and user.role in ['superadmin', 'admin']:
            return EVENLab.objects.all()
        
        return EVENLab.objects.filter(
            Q(server__created_by=user) | Q(created_by=user)
        ).distinct()
    
    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """Démarre le laboratoire"""
        lab = self.get_object()
        
        if not self._can_access_object(lab):
            self.permission_denied(request)
        
        client = lab.server.get_client()
        
        # Login si nécessaire
        login_result = client.login()
        if not login_result['success']:
            return error_response("Cannot login to EVE-NG server", login_result)
        
        result = client.start_lab(lab.lab_path)
        
        if result['success']:
            lab.status = 'running'
            lab.save()
            
            # Mettre à jour le statut des nœuds
            lab.nodes.update(status='running')
            
            return success_response(
                EVENLabDetailSerializer(lab).data,
                "Lab started successfully"
            )
        
        return error_response("Failed to start lab", result)
    
    @action(detail=True, methods=['post'])
    def stop(self, request, pk=None):
        """Arrête le laboratoire"""
        lab = self.get_object()
        
        if not self._can_access_object(lab):
            self.permission_denied(request)
        
        client = lab.server.get_client()
        
        # Login si nécessaire
        login_result = client.login()
        if not login_result['success']:
            return error_response("Cannot login to EVE-NG server", login_result)
        
        result = client.stop_lab(lab.lab_path)
        
        if result['success']:
            lab.status = 'stopped'
            lab.save()
            
            # Mettre à jour le statut des nœuds
            lab.nodes.update(status='stopped')
            
            return success_response(
                EVENLabDetailSerializer(lab).data,
                "Lab stopped successfully"
            )
        
        return error_response("Failed to stop lab", result)
    
    @action(detail=True, methods=['get'])
    def nodes(self, request, pk=None):
        """Liste les nœuds du laboratoire"""
        lab = self.get_object()
        
        if not self._can_access_object(lab):
            self.permission_denied(request)
        
        nodes = lab.nodes.all()
        page = self.paginate_queryset(nodes)
        
        if page is not None:
            serializer = EVENNodeSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = EVENNodeSerializer(nodes, many=True)
        return success_response(serializer.data, "Nodes retrieved")
    
    @action(detail=True, methods=['get'])
    def topology(self, request, pk=None):
        """Récupère la topologie du laboratoire"""
        lab = self.get_object()
        
        if not self._can_access_object(lab):
            self.permission_denied(request)
        
        topology = {
            'nodes': EVENNodeSerializer(lab.nodes.all(), many=True).data,
            'networks': EVENNetworkSerializer(lab.networks.all(), many=True).data,
            'links': EVENLinkSerializer(lab.links.all(), many=True).data
        }
        
        return success_response(topology, "Topology retrieved")
    
    def _can_access_object(self, obj):
        user = self.request.user
        if not user or not user.is_authenticated:
            return False
        
        if hasattr(user, 'role') and user.role in ['superadmin', 'admin']:
            return True
        
        return obj.server.created_by == user or obj.created_by == user


# ============================================================================
# NŒUDS EVE-NG
# ============================================================================

class EVENNodeViewSet(viewsets.ModelViewSet):
    """ViewSet pour les nœuds EVE-NG"""
    
    queryset = EVENNode.objects.select_related('lab', 'lab__server').all()
    serializer_class = EVENNodeSerializer
    permission_classes = [IsAuthenticated, IsActiveUser, HasAPIAccess]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_class = EVENNodeFilter
    search_fields = ['name', 'image', 'template']
    ordering_fields = ['name', 'node_id', 'created_at']
    ordering = ['lab', 'node_id']
    
    def get_queryset(self):
        user = self.request.user
        
        if not user or not user.is_authenticated:
            return EVENNode.objects.none()
        
        if hasattr(user, 'role') and user.role in ['superadmin', 'admin']:
            return EVENNode.objects.all()
        
        return EVENNode.objects.filter(lab__server__created_by=user)
    
    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """Démarre le nœud"""
        node = self.get_object()
        
        if not self._can_access_object(node):
            self.permission_denied(request)
        
        client = node.lab.server.get_client()
        
        # Login si nécessaire
        login_result = client.login()
        if not login_result['success']:
            return error_response("Cannot login to EVE-NG server", login_result)
        
        result = client.start_node(node.lab.lab_path, node.node_id)
        
        if result['success']:
            node.status = 'running'
            node.save()
            return success_response(
                EVENNodeSerializer(node).data,
                "Node started successfully"
            )
        
        return error_response("Failed to start node", result)
    
    @action(detail=True, methods=['post'])
    def stop(self, request, pk=None):
        """Arrête le nœud"""
        node = self.get_object()
        
        if not self._can_access_object(node):
            self.permission_denied(request)
        
        client = node.lab.server.get_client()
        
        # Login si nécessaire
        login_result = client.login()
        if not login_result['success']:
            return error_response("Cannot login to EVE-NG server", login_result)
        
        result = client.stop_node(node.lab.lab_path, node.node_id)
        
        if result['success']:
            node.status = 'stopped'
            node.save()
            return success_response(
                EVENNodeSerializer(node).data,
                "Node stopped successfully"
            )
        
        return error_response("Failed to stop node", result)
    
    def _can_access_object(self, obj):
        user = self.request.user
        if not user or not user.is_authenticated:
            return False
        
        if hasattr(user, 'role') and user.role in ['superadmin', 'admin']:
            return True
        
        return obj.lab.server.created_by == user


# ============================================================================
# RÉSEAUX EVE-NG
# ============================================================================

class EVENNetworkViewSet(viewsets.ModelViewSet):
    """ViewSet pour les réseaux EVE-NG"""
    
    queryset = EVENNetwork.objects.select_related('lab', 'lab__server').all()
    serializer_class = EVENNetworkSerializer
    permission_classes = [IsAuthenticated, IsActiveUser, HasAPIAccess]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_class = EVENNetworkFilter
    search_fields = ['name']
    ordering_fields = ['network_id', 'created_at']
    ordering = ['lab', 'network_id']
    
    def get_queryset(self):
        user = self.request.user
        
        if not user or not user.is_authenticated:
            return EVENNetwork.objects.none()
        
        if hasattr(user, 'role') and user.role in ['superadmin', 'admin']:
            return EVENNetwork.objects.all()
        
        return EVENNetwork.objects.filter(lab__server__created_by=user)


# ============================================================================
# LIENS EVE-NG
# ============================================================================

class EVENLinkViewSet(viewsets.ModelViewSet):
    """ViewSet pour les liens EVE-NG"""
    
    queryset = EVENLink.objects.select_related(
        'lab', 'lab__server', 'source_node', 'destination_node'
    ).all()
    serializer_class = EVENLinkSerializer
    permission_classes = [IsAuthenticated, IsActiveUser, HasAPIAccess]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_class = EVENLinkFilter
    search_fields = []
    ordering_fields = ['created_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        user = self.request.user
        
        if not user or not user.is_authenticated:
            return EVENLink.objects.none()
        
        if hasattr(user, 'role') and user.role in ['superadmin', 'admin']:
            return EVENLink.objects.all()
        
        return EVENLink.objects.filter(lab__server__created_by=user)


# ============================================================================
# IMAGES EVE-NG
# ============================================================================

class EVENImageViewSet(viewsets.ModelViewSet):
    """ViewSet pour les images EVE-NG"""
    
    queryset = EVENImage.objects.select_related('server').all()
    serializer_class = EVENImageSerializer
    permission_classes = [IsAuthenticated, IsActiveUser, HasAPIAccess]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_class = EVENImageFilter
    search_fields = ['name', 'description', 'version']
    ordering_fields = ['name', 'size_mb', 'created_at']
    ordering = ['name']
    
    def get_queryset(self):
        user = self.request.user
        
        if not user or not user.is_authenticated:
            return EVENImage.objects.none()
        
        if hasattr(user, 'role') and user.role in ['superadmin', 'admin']:
            return EVENImage.objects.all()
        
        return EVENImage.objects.filter(server__created_by=user)


# ============================================================================
# SESSIONS UTILISATEURS
# ============================================================================

class EVENUserSessionViewSet(viewsets.ModelViewSet):
    """ViewSet pour les sessions utilisateurs"""
    
    queryset = EVENUserSession.objects.select_related('server', 'user').all()
    serializer_class = EVENUserSessionSerializer
    permission_classes = [IsAuthenticated, IsActiveUser, HasAPIAccess]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_class = EVENUserSessionFilter
    search_fields = []
    ordering_fields = ['logged_in_at', 'last_activity_at']
    ordering = ['-last_activity_at']
    
    def get_queryset(self):
        user = self.request.user
        
        if not user or not user.is_authenticated:
            return EVENUserSession.objects.none()
        
        if hasattr(user, 'role') and user.role in ['superadmin', 'admin']:
            return EVENUserSession.objects.all()
        
        return EVENUserSession.objects.filter(user=user)
    
    @action(detail=True, methods=['post'])
    def logout(self, request, pk=None):
        """Déconnecte une session"""
        session = self.get_object()
        
        if not self._can_access_object(session):
            self.permission_denied(request)
        
        session.is_active = False
        session.save()
        
        return success_response(None, "Session closed")
    
    def _can_access_object(self, obj):
        user = self.request.user
        if not user or not user.is_authenticated:
            return False
        
        if hasattr(user, 'role') and user.role in ['superadmin', 'admin']:
            return True
        
        return obj.user == user


# ============================================================================
# DASHBOARD EVE-NG
# ============================================================================

class EVENDashboardViewSet(viewsets.ViewSet):
    """Dashboard pour EVE-NG"""
    permission_classes = [IsAuthenticated, IsActiveUser, HasAPIAccess]
    
    def _get_user_querysets(self, user):
        is_admin = hasattr(user, 'role') and user.role in ['superadmin', 'admin']
        
        if is_admin:
            servers = EVENServer.objects.all()
            labs = EVENLab.objects.all()
            nodes = EVENNode.objects.all()
            images = EVENImage.objects.all()
            sessions = EVENUserSession.objects.filter(is_active=True)
        else:
            servers = EVENServer.objects.filter(created_by=user)
            labs = EVENLab.objects.filter(server__created_by=user)
            nodes = EVENNode.objects.filter(lab__server__created_by=user)
            images = EVENImage.objects.filter(server__created_by=user)
            sessions = EVENUserSession.objects.filter(user=user, is_active=True)
        
        return servers, labs, nodes, images, sessions, is_admin
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Résumé des activités EVE-NG"""
        user = request.user
        
        if not user or not user.is_authenticated:
            return error_response("Authentication required")
        
        servers, labs, nodes, images, sessions, is_admin = self._get_user_querysets(user)
        
        running_labs = labs.filter(status='running')
        running_nodes = nodes.filter(status='running')
        
        # Labs par statut
        labs_by_status = list(
            labs.values('status').annotate(count=Count('id'))
        )
        
        # Nœuds par type
        nodes_by_type = list(
            nodes.values('node_type').annotate(count=Count('id'))
        )
        
        # Images les plus utilisées
        top_images = list(
            images.annotate(usage=Count('id')).order_by('-usage')[:10].values('name', 'usage')
        )
        
        data = {
            'statistics': {
                'total_servers': servers.count(),
                'active_servers': servers.filter(status='active').count(),
                'total_labs': labs.count(),
                'running_labs': running_labs.count(),
                'total_nodes': nodes.count(),
                'running_nodes': running_nodes.count(),
                'total_images': images.count(),
                'active_sessions': sessions.count(),
            },
            'recent_labs': [
                {
                    'id': str(l.id),
                    'name': l.name,
                    'server_name': l.server.name,
                    'status': l.get_status_display(),
                    'node_count': l.node_count,
                    'updated_at': l.updated_at
                }
                for l in labs.order_by('-updated_at')[:10]
            ],
            'labs_by_status': labs_by_status,
            'nodes_by_type': nodes_by_type,
            'top_images': top_images
        }
        
        return success_response(data, "Dashboard summary retrieved")
