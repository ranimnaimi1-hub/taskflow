# apps/ansible_app/views.py
"""
Ansible App Views - API endpoints professionnels
Version COMPLÈTE et CORRIGÉE
"""
from rest_framework import viewsets, status
from rest_framework import filters as drf_filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count, Q, Avg, Sum
from django.utils import timezone
from datetime import timedelta
import logging

# Import des permissions personnalisées depuis core
from apps.core.permissions import (
    IsActiveUser,
    HasAPIAccess,
    CanExecuteAnsible,
    IsAdmin
)
from apps.core.pagination import StandardPagination
from apps.core.responses import success_response, created_response, error_response

from .models import (
    AnsibleInventory, Playbook, PlaybookExecution, PlaybookSchedule,
    AnsibleRole, AnsibleCollection, AnsibleTask, AnsibleVars, AnsibleCredential
)
from .serializers import (
    AnsibleInventorySerializer, AnsibleInventoryDetailSerializer,
    PlaybookSerializer, PlaybookDetailSerializer,
    PlaybookExecutionSerializer, PlaybookExecutionDetailSerializer,
    PlaybookScheduleSerializer,
    AnsibleRoleSerializer,
    AnsibleCollectionSerializer,
    AnsibleTaskSerializer,
    AnsibleVarsSerializer,
    AnsibleCredentialSerializer,
    ExecutePlaybookRequestSerializer,
    GenerateInventorySerializer,
    AnsibleDashboardSerializer,
    DashboardStatisticsSerializer,
    RecentExecutionItemSerializer,
    TopPlaybookItemSerializer,
    UpcomingScheduleItemSerializer
)
from .executor import AnsibleExecutor
from .filters import (
    AnsibleInventoryFilter, 
    PlaybookFilter, 
    PlaybookExecutionFilter,
    PlaybookScheduleFilter, 
    AnsibleRoleFilter, 
    AnsibleCollectionFilter,
    AnsibleTaskFilter,
    AnsibleCredentialFilter  # Ajoutez celui-ci aussi
)
from .tasks import execute_playbook_task
from .validators import validate_playbook_content, validate_inventory_content

logger = logging.getLogger(__name__)


# ============================================================================
# INVENTAIRES ANSIBLE
# ============================================================================

class AnsibleInventoryViewSet(viewsets.ModelViewSet):
    """ViewSet pour les inventaires Ansible"""
    
    queryset = AnsibleInventory.objects.all()
    serializer_class = AnsibleInventorySerializer
    serializer_classes = {
        'retrieve': AnsibleInventoryDetailSerializer,
        'default': AnsibleInventorySerializer
    }
    
    permission_classes = [IsAuthenticated, IsActiveUser, HasAPIAccess, CanExecuteAnsible]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_class = AnsibleInventoryFilter
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        """Retourne le sérializer approprié selon l'action"""
        return self.serializer_classes.get(self.action, self.serializer_classes['default'])
    
    def get_queryset(self):
        """Filtre les inventaires selon l'utilisateur"""
        user = self.request.user
        
        # IMPORTANT: Vérifier si l'utilisateur est authentifié
        if not user or not user.is_authenticated:
            return AnsibleInventory.objects.none()
        
        # Vérifier si l'utilisateur a l'attribut 'role'
        if hasattr(user, 'role') and user.role in ['superadmin', 'admin']:
            return AnsibleInventory.objects.all()
        
        return AnsibleInventory.objects.filter(created_by=user)
    
    def perform_create(self, serializer):
        """Crée un inventaire avec l'utilisateur courant"""
        if self.request.user.is_authenticated:
            serializer.save(created_by=self.request.user)
        else:
            serializer.save()
    
    @action(detail=True, methods=['post'])
    def generate(self, request, pk=None):
        """Génère le contenu de l'inventaire"""
        inventory = self.get_object()
        
        if not self._can_access_object(inventory):
            self.permission_denied(request)
        
        content = inventory.generate_inventory_content()
        inventory.content = content
        inventory.save(update_fields=['content'])
        
        return success_response(
            {'content': content},
            "Inventory content generated"
        )
    
    @action(detail=True, methods=['post'])
    def validate(self, request, pk=None):
        """Valide le contenu de l'inventaire"""
        inventory = self.get_object()
        
        if not self._can_access_object(inventory):
            self.permission_denied(request)
        
        result = validate_inventory_content(
            inventory.content, 
            inventory.format
        )
        
        if result['valid']:
            return success_response(result, "Inventory is valid")
        return error_response("Inventory validation failed", result)
    
    @action(detail=False, methods=['post'])
    def generate_from_selection(self, request):
        """Génère un inventaire à partir d'une sélection"""
        serializer = GenerateInventorySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        
        # Récupérer les devices (import à l'intérieur pour éviter les imports circulaires)
        try:
            from apps.inventory.models import Device
        except ImportError:
            return error_response("Inventory app not available")
        
        devices = Device.objects.none()
        
        if data.get('device_ids'):
            devices = devices.union(Device.objects.filter(id__in=data['device_ids']))
        
        if data.get('site_ids'):
            devices = devices.union(Device.objects.filter(site_id__in=data['site_ids']))
        
        if data.get('cluster_ids'):
            devices = devices.union(Device.objects.filter(clusters__id__in=data['cluster_ids']))
        
        if data.get('tenant_ids'):
            devices = devices.union(Device.objects.filter(tenant_id__in=data['tenant_ids']))
        
        # Générer le contenu
        lines = []
        
        if data.get('variables'):
            lines.append("[all:vars]")
            for key, value in data['variables'].items():
                lines.append(f"{key}={value}")
            lines.append("")
        
        for device in devices.distinct():
            vars_list = [f"ansible_host={device.management_ip}"]
            if device.username:
                vars_list.append(f"ansible_user={device.username}")
            if device.ssh_port != 22:
                vars_list.append(f"ansible_port={device.ssh_port}")
            
            line = f"{device.hostname} {' '.join(vars_list)}"
            lines.append(line)
        
        content = "\n".join(lines)
        
        return success_response(
            {'content': content, 'hosts_count': devices.count()},
            "Inventory generated"
        )
    
    def _can_access_object(self, obj):
        """Vérifie si l'utilisateur peut accéder à l'objet"""
        user = self.request.user
        
        if not user or not user.is_authenticated:
            return False
            
        return (hasattr(user, 'role') and user.role in ['superadmin', 'admin']) or obj.created_by == user


# ============================================================================
# PLAYBOOKS - CORRIGÉ
# ============================================================================

class PlaybookViewSet(viewsets.ModelViewSet):
    """ViewSet pour les playbooks Ansible"""
    
    queryset = Playbook.objects.select_related('inventory', 'default_inventory', 'created_by').all()
    serializer_class = PlaybookSerializer
    serializer_classes = {
        'retrieve': PlaybookDetailSerializer,
        'default': PlaybookSerializer
    }
    
    permission_classes = [IsAuthenticated, IsActiveUser, HasAPIAccess]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_class = PlaybookFilter
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at', 'execution_count']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        """Retourne le sérializer approprié selon l'action"""
        return self.serializer_classes.get(self.action, self.serializer_classes['default'])
    
    def get_permissions(self):
        """Permissions différentes selon l'action"""
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'execute']:
            self.permission_classes = [IsAuthenticated, IsActiveUser, HasAPIAccess, CanExecuteAnsible]
        return [permission() for permission in self.permission_classes]
    
    def get_queryset(self):
        """Filtre les playbooks selon les permissions"""
        user = self.request.user
        
        # IMPORTANT: Vérifier si l'utilisateur est authentifié
        if not user or not user.is_authenticated:
            return Playbook.objects.none()
        
        if hasattr(user, 'role') and user.role in ['superadmin', 'admin']:
            return Playbook.objects.all()
        
        return Playbook.objects.filter(
            Q(created_by=user) | 
            Q(visibility='public') |
            (Q(visibility='shared') & Q(allowed_users=user))
        ).distinct()
    
    def perform_create(self, serializer):
        """Crée un playbook avec l'utilisateur courant"""
        if self.request.user.is_authenticated:
            serializer.save(created_by=self.request.user)
        else:
            serializer.save()
    
    @action(detail=True, methods=['post'])
    def execute(self, request, pk=None):
        """Exécute un playbook"""
        playbook = self.get_object()
        
        if not self._can_access_object(playbook):
            self.permission_denied(request, message="You don't have permission to access this playbook")
        
        # Validation des données
        req_serializer = ExecutePlaybookRequestSerializer(data=request.data)
        req_serializer.is_valid(raise_exception=True)
        data = req_serializer.validated_data
        
        # Déterminer l'inventaire à utiliser
        inventory = None
        if data.get('inventory_id'):
            try:
                inventory = AnsibleInventory.objects.get(id=data['inventory_id'])
            except AnsibleInventory.DoesNotExist:
                pass
        else:
            inventory = playbook.inventory or playbook.default_inventory
        
        if not inventory:
            return error_response("No inventory specified for execution")
        
        # Créer l'exécution
        execution = PlaybookExecution.objects.create(
            playbook=playbook,
            inventory=inventory,
            extra_vars=data.get('extra_vars', {}),
            limit=data.get('limit', ''),
            tags=data.get('tags', []),
            skip_tags=data.get('skip_tags', []),
            check_mode=data.get('check_mode', False),
            diff_mode=data.get('diff_mode', False),
            executed_by=request.user if request.user.is_authenticated else None,
            status='pending'
        )
        
        # Prendre un snapshot de l'inventaire
        execution.take_inventory_snapshot()
        
        # Lancer l'exécution asynchrone
        try:
            execute_playbook_task.delay(str(execution.id))
        except Exception as e:
            logger.error(f"Failed to start async task: {e}")
        
        return created_response(
            PlaybookExecutionSerializer(execution).data,
            "Playbook execution started"
        )
    
    @action(detail=True, methods=['post'])
    def validate(self, request, pk=None):
        """Valide la syntaxe du playbook"""
        playbook = self.get_object()
        
        if not self._can_access_object(playbook):
            self.permission_denied(request)
        
        result = validate_playbook_content(playbook.content)
        
        if result['valid']:
            return success_response(result, "Playbook is valid")
        return error_response("Playbook validation failed", result)
    
    @action(detail=True, methods=['get'])
    def executions(self, request, pk=None):
        """Liste les exécutions du playbook"""
        playbook = self.get_object()
        
        if not self._can_access_object(playbook):
            self.permission_denied(request)
        
        executions = playbook.executions.all()
        
        page = self.paginate_queryset(executions)
        if page is not None:
            serializer = PlaybookExecutionSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = PlaybookExecutionSerializer(executions, many=True)
        return success_response(serializer.data, "Executions retrieved")
    
    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        """Statistiques du playbook"""
        playbook = self.get_object()
        
        if not self._can_access_object(playbook):
            self.permission_denied(request)
        
        last_execution = None
        if playbook.last_execution:
            last_execution = {
                'id': str(playbook.last_execution.id),
                'status': playbook.last_execution.status,
                'created_at': playbook.last_execution.created_at.isoformat() if playbook.last_execution.created_at else None
            }
        
        data = {
            'execution_count': playbook.execution_count,
            'success_count': playbook.success_count,
            'failure_count': playbook.failure_count,
            'success_rate': playbook.success_rate,
            'avg_duration': playbook.avg_duration,
            'last_execution': last_execution
        }
        
        return success_response(data, "Statistics retrieved")
    
    def _can_access_object(self, obj):
        """Vérifie si l'utilisateur peut accéder à l'objet"""
        user = self.request.user
        
        if not user or not user.is_authenticated:
            return False
        
        if hasattr(user, 'role') and user.role in ['superadmin', 'admin']:
            return True
        
        if obj.visibility == 'public':
            return True
        elif obj.visibility == 'shared' and obj.allowed_users.filter(id=user.id).exists():
            return True
        elif obj.created_by == user:
            return True
        
        return False
    
    
    

# ============================================================================
# PLAYBOOK EXECUTIONS - CORRIGÉ
# ============================================================================

class PlaybookExecutionViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet pour les exécutions de playbooks (lecture seule)"""
    
    queryset = PlaybookExecution.objects.select_related('playbook', 'inventory', 'executed_by').all()
    serializer_class = PlaybookExecutionSerializer
    serializer_classes = {
        'retrieve': PlaybookExecutionDetailSerializer,
        'default': PlaybookExecutionSerializer
    }
    
    permission_classes = [IsAuthenticated, IsActiveUser, HasAPIAccess]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_class = PlaybookExecutionFilter
    search_fields = ['playbook__name']
    ordering_fields = ['created_at', 'started_at', 'completed_at', 'duration']
    ordering = ['-created_at']

    def get_serializer_class(self):
        """Retourne le sérializer approprié selon l'action"""
        return self.serializer_classes.get(self.action, self.serializer_classes['default'])
    
    def get_queryset(self):
        """Filtre les exécutions selon l'utilisateur"""
        user = self.request.user
        
        # IMPORTANT: Vérifier si l'utilisateur est authentifié
        if not user or not user.is_authenticated:
            return PlaybookExecution.objects.none()
        
        if hasattr(user, 'role') and user.role in ['superadmin', 'admin']:
            return PlaybookExecution.objects.all()
        
        return PlaybookExecution.objects.filter(
            Q(executed_by=user) | Q(playbook__created_by=user)
        ).distinct()
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Annule une exécution en cours"""
        execution = self.get_object()
        
        if not self._can_cancel(execution):
            self.permission_denied(request, message="You don't have permission to cancel this execution")
        
        if execution.status not in ['pending', 'running']:
            return error_response(f"Cannot cancel execution with status: {execution.status}")
        
        execution.status = 'cancelled'
        execution.completed_at = timezone.now()
        execution.save(update_fields=['status', 'completed_at'])
        
        return success_response(
            PlaybookExecutionSerializer(execution).data,
            "Execution cancelled"
        )
    
    @action(detail=True, methods=['get'])
    def output(self, request, pk=None):
        """Récupère la sortie formatée"""
        execution = self.get_object()
        
        if not self._can_view(execution):
            self.permission_denied(request)
        
        return Response({
            'stdout': execution.output,
            'stderr': execution.error_output,
            'summary': execution.summary,
            'host_results': execution.host_results
        })
    
    def _can_view(self, obj):
        user = self.request.user
        
        if not user or not user.is_authenticated:
            return False
            
        return (hasattr(user, 'role') and user.role in ['superadmin', 'admin'] or 
                obj.executed_by == user or 
                obj.playbook.created_by == user)
    
    def _can_cancel(self, obj):
        user = self.request.user
        
        if not user or not user.is_authenticated:
            return False
            
        return (hasattr(user, 'role') and user.role in ['superadmin', 'admin'] or 
                obj.executed_by == user)
    

# ============================================================================
# PLAYBOOK SCHEDULES - CORRIGÉ
# ============================================================================

class PlaybookScheduleViewSet(viewsets.ModelViewSet):
    """ViewSet pour les planifications de playbooks"""
    
    queryset = PlaybookSchedule.objects.select_related('playbook', 'inventory', 'created_by').all()
    serializer_class = PlaybookScheduleSerializer
    
    permission_classes = [IsAuthenticated, IsActiveUser, HasAPIAccess, CanExecuteAnsible]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_class = PlaybookScheduleFilter
    search_fields = ['name']
    ordering_fields = ['next_run', 'created_at']
    ordering = ['next_run']
    
    def get_queryset(self):
        """Filtre les planifications selon l'utilisateur"""
        user = self.request.user
        
        # IMPORTANT: Vérifier si l'utilisateur est authentifié
        if not user or not user.is_authenticated:
            return PlaybookSchedule.objects.none()
        
        if hasattr(user, 'role') and user.role in ['superadmin', 'admin']:
            return PlaybookSchedule.objects.all()
        
        return PlaybookSchedule.objects.filter(created_by=user)
    
    def perform_create(self, serializer):
        """Crée une planification avec l'utilisateur courant"""
        if self.request.user.is_authenticated:
            schedule = serializer.save(created_by=self.request.user)
        else:
            schedule = serializer.save()
        
        schedule.next_run = schedule.calculate_next_run()
        schedule.save(update_fields=['next_run'])
    
    @action(detail=True, methods=['post'])
    def pause(self, request, pk=None):
        """Met en pause la planification"""
        schedule = self.get_object()
        
        if not self._check_owner(schedule):
            self.permission_denied(request)
        
        schedule.status = 'paused'
        schedule.save(update_fields=['status'])
        
        return success_response(
            PlaybookScheduleSerializer(schedule).data,
            "Schedule paused"
        )
    
    @action(detail=True, methods=['post'])
    def resume(self, request, pk=None):
        """Reprend la planification"""
        schedule = self.get_object()
        
        if not self._check_owner(schedule):
            self.permission_denied(request)
        
        schedule.status = 'active'
        schedule.next_run = schedule.calculate_next_run()
        schedule.save(update_fields=['status', 'next_run'])
        
        return success_response(
            PlaybookScheduleSerializer(schedule).data,
            "Schedule resumed"
        )
    
    @action(detail=True, methods=['post'])
    def run_now(self, request, pk=None):
        """Exécute immédiatement la planification"""
        schedule = self.get_object()
        
        if not self._check_owner(schedule):
            self.permission_denied(request)
        
        # Créer une exécution
        execution = PlaybookExecution.objects.create(
            playbook=schedule.playbook,
            inventory=schedule.inventory,
            extra_vars=schedule.extra_vars,
            limit=schedule.limit,
            tags=schedule.tags,
            check_mode=schedule.check_mode,
            executed_by=request.user if request.user.is_authenticated else None,
            status='pending'
        )
        
        try:
            execute_playbook_task.delay(str(execution.id))
        except Exception as e:
            logger.error(f"Failed to start async task: {e}")
        
        return success_response(
            PlaybookExecutionSerializer(execution).data,
            "Execution started"
        )
    
    @action(detail=True, methods=['get'])
    def executions(self, request, pk=None):
        """Liste les exécutions de cette planification"""
        schedule = self.get_object()
        
        if not self._check_owner(schedule):
            self.permission_denied(request)
        
        executions = PlaybookExecution.objects.filter(
            playbook=schedule.playbook,
            created_at__gte=schedule.start_date
        )
        
        page = self.paginate_queryset(executions)
        if page is not None:
            serializer = PlaybookExecutionSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = PlaybookExecutionSerializer(executions, many=True)
        return success_response(serializer.data, "Executions retrieved")
    
    def _check_owner(self, obj):
        """Vérifie que l'utilisateur est propriétaire"""
        user = self.request.user
        
        if not user or not user.is_authenticated:
            return False
            
        return (hasattr(user, 'role') and user.role in ['superadmin', 'admin']) or obj.created_by == user
    


# ============================================================================
# RÔLES ANSIBLE - CORRIGÉ
# ============================================================================

class AnsibleRoleViewSet(viewsets.ModelViewSet):
    """ViewSet pour les rôles Ansible"""
    queryset = AnsibleRole.objects.all()
    serializer_class = AnsibleRoleSerializer
    permission_classes = [IsAuthenticated, IsActiveUser, HasAPIAccess]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_class = AnsibleRoleFilter
    search_fields = ['name', 'namespace', 'description']
    ordering_fields = ['name', 'download_count', 'created_at']
    ordering = ['namespace', 'name']
    
    def get_queryset(self):
        user = self.request.user
        
        # IMPORTANT: Vérifier si l'utilisateur est authentifié
        if not user or not user.is_authenticated:
            return AnsibleRole.objects.none()
            
        return super().get_queryset()
    

# ============================================================================
# COLLECTIONS ANSIBLE - CORRIGÉ
# ============================================================================

class AnsibleCollectionViewSet(viewsets.ModelViewSet):
    """ViewSet pour les collections Ansible"""
    queryset = AnsibleCollection.objects.all()
    serializer_class = AnsibleCollectionSerializer
    permission_classes = [IsAuthenticated, IsActiveUser, HasAPIAccess]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_class = AnsibleCollectionFilter
    search_fields = ['name', 'namespace', 'description']
    ordering_fields = ['name', 'installed_at', 'created_at']
    ordering = ['namespace', 'name']
    
    def get_queryset(self):
        user = self.request.user
        
        # IMPORTANT: Vérifier si l'utilisateur est authentifié
        if not user or not user.is_authenticated:
            return AnsibleCollection.objects.none()
            
        return super().get_queryset()
    
# ============================================================================
# TÂCHES ANSIBLE - CORRIGÉ
# ============================================================================

class AnsibleTaskViewSet(viewsets.ModelViewSet):
    """ViewSet pour les tâches Ansible"""
    queryset = AnsibleTask.objects.all()
    serializer_class = AnsibleTaskSerializer
    permission_classes = [IsAuthenticated, IsActiveUser, HasAPIAccess, CanExecuteAnsible]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_class = AnsibleTaskFilter
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    def get_queryset(self):
        user = self.request.user
        
        # IMPORTANT: Vérifier si l'utilisateur est authentifié
        if not user or not user.is_authenticated:
            return AnsibleTask.objects.none()
            
        if hasattr(user, 'role') and user.role in ['superadmin', 'admin']:
            return AnsibleTask.objects.all()
            
        return AnsibleTask.objects.filter(created_by=user)
    
    def perform_create(self, serializer):
        if self.request.user.is_authenticated:
            serializer.save(created_by=self.request.user)
        else:
            serializer.save()
    

# ============================================================================
# VARIABLES ANSIBLE - CORRIGÉ
# ============================================================================

class AnsibleVarsViewSet(viewsets.ModelViewSet):
    """ViewSet pour les variables Ansible"""
    queryset = AnsibleVars.objects.all()
    serializer_class = AnsibleVarsSerializer
    permission_classes = [IsAuthenticated, IsActiveUser, HasAPIAccess, CanExecuteAnsible]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_fields = ['tenant', 'inventory', 'playbook']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    def get_queryset(self):
        user = self.request.user
        
        # IMPORTANT: Vérifier si l'utilisateur est authentifié
        if not user or not user.is_authenticated:
            return AnsibleVars.objects.none()
            
        if hasattr(user, 'role') and user.role in ['superadmin', 'admin']:
            return AnsibleVars.objects.all()
            
        return AnsibleVars.objects.filter(created_by=user)
    
    def perform_create(self, serializer):
        if self.request.user.is_authenticated:
            serializer.save(created_by=self.request.user)
        else:
            serializer.save()
    

# ============================================================================
# CREDENTIALS ANSIBLE - CORRIGÉ
# ============================================================================

class AnsibleCredentialViewSet(viewsets.ModelViewSet):
    """ViewSet pour les credentials Ansible"""
    queryset = AnsibleCredential.objects.all()
    serializer_class = AnsibleCredentialSerializer
    permission_classes = [IsAuthenticated, IsActiveUser, HasAPIAccess, CanExecuteAnsible]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_class = AnsibleCredentialFilter
    search_fields = ['name', 'username', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    def get_queryset(self):
        user = self.request.user
        
        # IMPORTANT: Vérifier si l'utilisateur est authentifié
        if not user or not user.is_authenticated:
            return AnsibleCredential.objects.none()
            
        if hasattr(user, 'role') and user.role in ['superadmin', 'admin']:
            return AnsibleCredential.objects.all()
            
        return AnsibleCredential.objects.filter(created_by=user)
    
    def perform_create(self, serializer):
        if self.request.user.is_authenticated:
            serializer.save(created_by=self.request.user)
        else:
            serializer.save()
    

# ============================================================================
# DASHBOARD - CORRIGÉ COMPLÈTEMENT
# ============================================================================

class AnsibleDashboardViewSet(viewsets.ViewSet):
    """Dashboard pour Ansible"""
    permission_classes = [IsAuthenticated, IsActiveUser, HasAPIAccess]

    def _get_user_querysets(self, user):
        """Retourne les querysets filtrés selon l'utilisateur"""
        # Vérifier si l'utilisateur est admin
        is_admin = hasattr(user, 'role') and user.role in ['superadmin', 'admin']
        
        if is_admin:
            playbooks = Playbook.objects.all()
            executions = PlaybookExecution.objects.all()
            inventories = AnsibleInventory.objects.all()
            schedules = PlaybookSchedule.objects.filter(status='active')
        else:
            playbooks = Playbook.objects.filter(
                Q(created_by=user) | Q(visibility='public') |
                (Q(visibility='shared') & Q(allowed_users=user))
            )
            executions = PlaybookExecution.objects.filter(
                Q(executed_by=user) | Q(playbook__created_by=user)
            )
            inventories = AnsibleInventory.objects.filter(created_by=user)
            schedules = PlaybookSchedule.objects.filter(
                created_by=user, status='active'
            )
        
        return playbooks, executions, inventories, schedules
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Résumé des activités Ansible"""
        user = request.user
        
        # IMPORTANT: Vérifier si l'utilisateur est authentifié
        if not user or not user.is_authenticated:
            return error_response("Authentication required")
        
        playbooks, executions, inventories, schedules = self._get_user_querysets(user)
        
        # Statistiques
        total_playbooks = playbooks.count()
        active_playbooks = playbooks.filter(status='active').count()
        total_inventories = inventories.count()
        
        last_24h = timezone.now() - timedelta(hours=24)
        recent_executions = executions.filter(created_at__gte=last_24h)
        
        successful = recent_executions.filter(status='completed').count()
        total_recent = recent_executions.count()
        success_rate = (successful / total_recent * 100) if total_recent > 0 else 0
        
        # Durée moyenne
        avg_duration = recent_executions.aggregate(
            avg=Avg('duration')
        )['avg'] or 0
        
        # Construction manuelle des données pour éviter les problèmes de sérialisation
        recent_executions_data = []
        for e in executions.order_by('-created_at')[:10]:
            recent_executions_data.append({
                'id': str(e.id),
                'playbook_name': e.playbook.name if e.playbook else None,
                'status': e.status,
                'created_at': e.created_at.isoformat() if e.created_at else None,
                'executed_by': e.executed_by.get_full_name() if e.executed_by else None
            })
        
        top_playbooks_data = []
        for p in playbooks.annotate(exec_count=Count('executions')).order_by('-exec_count')[:5]:
            top_playbooks_data.append({
                'id': str(p.id),
                'name': p.name,
                'execution_count': p.execution_count,
                'success_rate': p.success_rate
            })
        
        upcoming_schedules_data = []
        for s in schedules.filter(next_run__isnull=False).order_by('next_run')[:5]:
            upcoming_schedules_data.append({
                'id': str(s.id),
                'name': s.name,
                'playbook_name': s.playbook.name if s.playbook else None,
                'next_run': s.next_run.isoformat() if s.next_run else None,
                'schedule_type': s.schedule_type
            })
        
        data = {
            'statistics': {
                'total_playbooks': total_playbooks,
                'active_playbooks': active_playbooks,
                'total_inventories': total_inventories,
                'total_schedules': schedules.count(),
                'executions_24h': total_recent,
                'successful_24h': successful,
                'failed_24h': total_recent - successful,
                'success_rate_24h': round(success_rate, 2),
                'avg_duration_24h': round(avg_duration, 2)
            },
            'recent_executions': recent_executions_data,
            'top_playbooks': top_playbooks_data,
            'upcoming_schedules': upcoming_schedules_data
        }
        
        return success_response(data, "Dashboard summary retrieved")
    
    @action(detail=False, methods=['get'])
    def charts(self, request):
        """Données pour les graphiques"""
        user = request.user
        
        # IMPORTANT: Vérifier si l'utilisateur est authentifié
        if not user or not user.is_authenticated:
            return error_response("Authentication required")
        
        # Base queryset
        if hasattr(user, 'role') and user.role in ['superadmin', 'admin']:
            executions = PlaybookExecution.objects.all()
            playbooks = Playbook.objects.all()
        else:
            executions = PlaybookExecution.objects.filter(
                Q(executed_by=user) | Q(playbook__created_by=user)
            )
            playbooks = Playbook.objects.filter(
                Q(created_by=user) | Q(visibility='public')
            )
        
        # Exécutions par statut
        by_status = list(executions.values('status').annotate(
            count=Count('id')
        ))
        
        # Exécutions par jour (7 derniers jours)
        last_7_days = timezone.now() - timedelta(days=7)
        by_day = list(executions.filter(
            created_at__gte=last_7_days
        ).extra(
            {'day': "date(created_at)"}
        ).values('day').annotate(
            count=Count('id'),
            success=Count('id', filter=Q(status='completed'))
        ).order_by('day'))
        
        # Top playbooks par exécutions
        top_playbooks = list(playbooks.annotate(
            exec_count=Count('executions')
        ).order_by('-exec_count')[:10].values('name', 'exec_count'))
        
        data = {
            'by_status': by_status,
            'by_day': by_day,
            'top_playbooks': top_playbooks,
            'success_rate_trend': []
        }
        
        return success_response(data, "Chart data retrieved")
    
