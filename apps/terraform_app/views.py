# apps/terraform_app/views.py
"""
Terraform App Views - API endpoints professionnels avec executor intégré
"""
from rest_framework import viewsets, status
from rest_framework import filters as drf_filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count, Avg
from django.utils import timezone
from datetime import timedelta
import logging
import os
import tempfile

from apps.core.permissions import IsActiveUser, HasAPIAccess, CanExecuteAnsible
from apps.core.pagination import StandardPagination
from apps.core.responses import success_response, created_response, error_response

from .models import (
    TerraformConfig, TerraformPlan, TerraformApply, TerraformState,
    TerraformModule, TerraformProvider, TerraformVariable, TerraformCredential
)
from .serializers import (
    TerraformConfigSerializer, TerraformConfigDetailSerializer,
    TerraformPlanSerializer, TerraformPlanDetailSerializer,
    TerraformApplySerializer, TerraformApplyDetailSerializer,
    TerraformStateSerializer, TerraformStateDetailSerializer,
    TerraformModuleSerializer,
    TerraformProviderSerializer,
    TerraformVariableSerializer,
    TerraformCredentialSerializer,
    TerraformPlanRequestSerializer,
    TerraformApplyRequestSerializer,
    TerraformDestroyRequestSerializer,
)
from .filters import (
    TerraformConfigFilter,
    TerraformPlanFilter,
    TerraformApplyFilter,
    TerraformStateFilter,
    TerraformModuleFilter,
    TerraformProviderFilter,
    TerraformVariableFilter,
    TerraformCredentialFilter,
)
from .executor import TerraformExecutor  # ← IMPORT DE L'EXECUTOR

logger = logging.getLogger(__name__)


# ============================================================================
# FONCTIONS UTILITAIRES
# ============================================================================

def create_temp_config_dir(config):
    """
    Crée un répertoire temporaire avec les fichiers de configuration Terraform
    
    Args:
        config (TerraformConfig): La configuration Terraform
        
    Returns:
        str: Chemin du répertoire temporaire
    """
    temp_dir = tempfile.mkdtemp(prefix=f"terraform_{config.name}_")
    
    # Écrire les fichiers de configuration
    files = config.get_full_config()
    for filename, content in files.items():
        if content:
            file_path = os.path.join(temp_dir, filename)
            with open(file_path, 'w') as f:
                f.write(content)
    
    return temp_dir


# ============================================================================
# CONFIGURATIONS TERRAFORM
# ============================================================================

class TerraformConfigViewSet(viewsets.ModelViewSet):
    """ViewSet pour les configurations Terraform avec exécution réelle"""
    
    queryset = TerraformConfig.objects.select_related(
        'site', 'cluster', 'tenant', 'created_by'
    ).prefetch_related('allowed_users', 'credentials').all()
    
    serializer_class = TerraformConfigSerializer
    serializer_classes = {
        'retrieve': TerraformConfigDetailSerializer,
        'default': TerraformConfigSerializer
    }
    
    permission_classes = [IsAuthenticated, IsActiveUser, HasAPIAccess]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_class = TerraformConfigFilter
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at', 'apply_count']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        return self.serializer_classes.get(self.action, self.serializer_classes['default'])
    
    def get_queryset(self):
        user = self.request.user
        
        if not user or not user.is_authenticated:
            return TerraformConfig.objects.none()
        
        if hasattr(user, 'role') and user.role in ['superadmin', 'admin']:
            return TerraformConfig.objects.all()
        
        return TerraformConfig.objects.filter(
            Q(created_by=user) | Q(allowed_users=user)
        ).distinct()
    
    def perform_create(self, serializer):
        if self.request.user.is_authenticated:
            serializer.save(created_by=self.request.user)
        else:
            serializer.save()
    
    @action(detail=True, methods=['post'])
    def execute_plan(self, request, pk=None):  # ← Renommé de plan à execute_plan
        """Exécute terraform plan sur la configuration"""
        config = self.get_object()
        
        if not self._can_access_object(config):
            self.permission_denied(request)
        
        serializer = TerraformDestroyRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        
        temp_dir = None
        try:
            temp_dir = create_temp_config_dir(config)
            
            executor = TerraformExecutor()
            
            # Initialiser Terraform
            init_result = executor.init(temp_dir)
            if not init_result['success']:
                return error_response(
                    "Terraform init failed",
                    {'stderr': init_result.get('stderr', '')}
                )
            
            # Exécuter destroy
            destroy_result = executor.destroy(
                temp_dir,
                auto_approve=data.get('auto_approve', False)
            )
            
            # Créer l'enregistrement d'apply (destroy est aussi un apply)
            apply = TerraformApply.objects.create(
                config=config,
                status='completed' if destroy_result['success'] else 'failed',
                stdout=destroy_result.get('stdout', ''),
                stderr=destroy_result.get('stderr', ''),
                return_code=0 if destroy_result['success'] else 1,
                executed_by=request.user if request.user.is_authenticated else None,
                started_at=timezone.now(),
                completed_at=timezone.now(),
            )
            
            return success_response(
                TerraformApplySerializer(apply).data,
                "Destroy completed successfully" if destroy_result['success'] else "Destroy failed"
            )
            
        except Exception as e:
            logger.exception(f"Error executing destroy: {str(e)}")
            return error_response(f"Destroy execution error: {str(e)}")
        finally:
            if temp_dir and os.path.exists(temp_dir):
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)
    
    @action(detail=True, methods=['post'])
    def execute_apply(self, request, pk=None):  # ← Renommé de apply à execute_apply
        """Exécute terraform apply sur la configuration"""
        config = self.get_object()
        
        if not self._can_access_object(config):
            self.permission_denied(request)
        
        serializer = TerraformApplyRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        
        temp_dir = None
        try:
            temp_dir = create_temp_config_dir(config)
            
            executor = TerraformExecutor()
            
            # Initialiser Terraform
            init_result = executor.init(temp_dir)
            if not init_result['success']:
                return error_response(
                    "Terraform init failed",
                    {'stderr': init_result.get('stderr', '')}
                )
            
            # Exécuter apply
            apply_result = executor.apply(
                temp_dir,
                plan_file=data.get('plan_file'),
                auto_approve=data.get('auto_approve', False)
            )
            
            # Récupérer les outputs
            outputs = {}
            if apply_result['success']:
                output_result = executor.output(temp_dir)
                if output_result['success']:
                    outputs = output_result.get('outputs', {})
            
            # Récupérer l'état
            state_json = {}
            if apply_result['success']:
                state_result = executor.show_state(temp_dir)
                if state_result['success']:
                    state_json = state_result.get('state', {})
            
            # Créer l'enregistrement d'apply
            apply = TerraformApply.objects.create(
                config=config,
                status='completed' if apply_result['success'] else 'failed',
                stdout=apply_result.get('stdout', ''),
                stderr=apply_result.get('stderr', ''),
                return_code=0 if apply_result['success'] else 1,
                outputs=outputs,
                state_json=state_json,
                executed_by=request.user if request.user.is_authenticated else None,
                started_at=timezone.now(),
                completed_at=timezone.now(),
            )
            
            # Créer un snapshot d'état
            if state_json:
                # Trouver la prochaine version
                last_state = TerraformState.objects.filter(config=config).order_by('-version').first()
                version = (last_state.version + 1) if last_state else 1
                
                TerraformState.objects.create(
                    config=config,
                    apply=apply,
                    state_json=state_json,
                    version=version,
                    resources_count=len(state_json.get('resources', [])),
                )
            
            # Mettre à jour les stats de la config
            config.apply_count += 1
            config.last_apply_status = 'completed' if apply_result['success'] else 'failed'
            config.last_apply_at = timezone.now()
            config.save(update_fields=['apply_count', 'last_apply_status', 'last_apply_at'])
            
            return created_response(
                TerraformApplySerializer(apply).data,
                "Apply completed successfully" if apply_result['success'] else "Apply failed"
            )
            
        except Exception as e:
            logger.exception(f"Error executing apply: {str(e)}")
            return error_response(f"Apply execution error: {str(e)}")
        finally:
            if temp_dir and os.path.exists(temp_dir):
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)
    
    @action(detail=True, methods=['post'])
    def execute_destroy(self, request, pk=None):  # ← Renommé de destroy à execute_destroy
        """Exécute terraform destroy sur la configuration"""
        config = self.get_object()
        
        if not self._can_access_object(config):
            self.permission_denied(request)
        
        serializer = TerraformDestroyRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        
        temp_dir = None
        try:
            temp_dir = create_temp_config_dir(config)
            
            executor = TerraformExecutor()
            
            # Initialiser Terraform
            init_result = executor.init(temp_dir)
            if not init_result['success']:
                return error_response(
                    "Terraform init failed",
                    {'stderr': init_result.get('stderr', '')}
                )
            
            # Exécuter destroy
            destroy_result = executor.destroy(
                temp_dir,
                auto_approve=data.get('auto_approve', False)
            )
            
            # Créer l'enregistrement d'apply (destroy est aussi un apply)
            apply = TerraformApply.objects.create(
                config=config,
                status='completed' if destroy_result['success'] else 'failed',
                stdout=destroy_result.get('stdout', ''),
                stderr=destroy_result.get('stderr', ''),
                return_code=0 if destroy_result['success'] else 1,
                executed_by=request.user if request.user.is_authenticated else None,
                started_at=timezone.now(),
                completed_at=timezone.now(),
            )
            
            return success_response(
                TerraformApplySerializer(apply).data,
                "Destroy completed successfully" if destroy_result['success'] else "Destroy failed"
            )
            
        except Exception as e:
            logger.exception(f"Error executing destroy: {str(e)}")
            return error_response(f"Destroy execution error: {str(e)}")
        finally:
            if temp_dir and os.path.exists(temp_dir):
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)
    
    @action(detail=True, methods=['get'])
    def validate_config(self, request, pk=None):  # ← Renommé de validate à validate_config
        """Valide la configuration Terraform avec terraform validate"""
        config = self.get_object()
        
        if not self._can_access_object(config):
            self.permission_denied(request)
        
        # Validation statique d'abord
        static_result = config.validate_config()
        if not static_result['valid']:
            return error_response("Configuration validation failed", static_result)
        
        # Validation avec terraform validate
        temp_dir = None
        try:
            temp_dir = create_temp_config_dir(config)
            
            executor = TerraformExecutor()
            
            # Exécuter terraform init d'abord (parfois nécessaire pour validate)
            init_result = executor.init(temp_dir)
            if not init_result['success']:
                return error_response(
                    "Terraform init failed",
                    {'stderr': init_result.get('stderr', '')}
                )
            
            # Exécuter validate
            validate_result = executor.validate(temp_dir)
            
            return success_response(
                validate_result,
                "Configuration is valid" if validate_result.get('valid') else "Configuration is invalid"
            )
            
        except Exception as e:
            logger.exception(f"Error validating config: {str(e)}")
            return error_response(f"Validation error: {str(e)}")
        finally:
            if temp_dir and os.path.exists(temp_dir):
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)
    
    @action(detail=True, methods=['get'])
    def get_outputs(self, request, pk=None):  # ← Renommé de output à get_outputs
        """Récupère les outputs de la configuration"""
        config = self.get_object()
        
        if not self._can_access_object(config):
            self.permission_denied(request)
        
        temp_dir = None
        try:
            temp_dir = create_temp_config_dir(config)
            
            executor = TerraformExecutor()
            
            # Récupérer les outputs
            output_result = executor.output(temp_dir)
            
            if output_result['success']:
                return success_response(
                    output_result.get('outputs', {}),
                    "Outputs retrieved successfully"
                )
            else:
                return error_response(
                    "Failed to retrieve outputs",
                    {'error': output_result.get('error')}
                )
                
        except Exception as e:
            logger.exception(f"Error getting outputs: {str(e)}")
            return error_response(f"Output error: {str(e)}")
        finally:
            if temp_dir and os.path.exists(temp_dir):
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)
    
    @action(detail=True, methods=['get'])
    def get_state(self, request, pk=None):  # ← Renommé de state à get_state
        """Récupère l'état actuel de la configuration"""
        config = self.get_object()
        
        if not self._can_access_object(config):
            self.permission_denied(request)
        
        # Chercher le dernier état en base
        latest_state = config.states.order_by('-version').first()
        
        if latest_state:
            serializer = TerraformStateSerializer(latest_state)
            return success_response(serializer.data, "State retrieved from database")
        else:
            # Sinon, essayer de récupérer depuis Terraform
            temp_dir = None
            try:
                temp_dir = create_temp_config_dir(config)
                
                executor = TerraformExecutor()
                state_result = executor.show_state(temp_dir)
                
                if state_result['success']:
                    return success_response(
                        state_result.get('state', {}),
                        "State retrieved from Terraform"
                    )
                else:
                    return success_response(
                        {},
                        "No state found"
                    )
                    
            except Exception as e:
                logger.exception(f"Error getting state: {str(e)}")
                return error_response(f"State error: {str(e)}")
            finally:
                if temp_dir and os.path.exists(temp_dir):
                    import shutil
                    shutil.rmtree(temp_dir, ignore_errors=True)
    
    @action(detail=True, methods=['post'])
    def format_files(self, request, pk=None):  # ← Renommé de format à format_files
        """Formate les fichiers de configuration"""
        config = self.get_object()
        
        if not self._can_access_object(config):
            self.permission_denied(request)
        
        temp_dir = None
        try:
            temp_dir = create_temp_config_dir(config)
            
            executor = TerraformExecutor()
            format_result = executor.format_check(temp_dir)
            
            # Note: terraform fmt -check ne formate pas, il vérifie seulement
            # Pour formater, il faudrait exécuter terraform fmt sans -check
            
            return success_response(
                format_result,
                "Format check completed"
            )
            
        except Exception as e:
            logger.exception(f"Error checking format: {str(e)}")
            return error_response(f"Format error: {str(e)}")
        finally:
            if temp_dir and os.path.exists(temp_dir):
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)
    
    def _can_access_object(self, obj):
        user = self.request.user
        if not user or not user.is_authenticated:
            return False
        
        if hasattr(user, 'role') and user.role in ['superadmin', 'admin']:
            return True
        
        if obj.created_by == user or user in obj.allowed_users.all():
            return True
        
        return False


# ============================================================================
# PLANS TERRAFORM (lecture seule)
# ============================================================================

class TerraformPlanViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet pour les plans Terraform (lecture seule)"""
    
    queryset = TerraformPlan.objects.select_related('config', 'executed_by').all()
    serializer_class = TerraformPlanSerializer
    serializer_classes = {
        'retrieve': TerraformPlanDetailSerializer,
        'default': TerraformPlanSerializer
    }
    
    permission_classes = [IsAuthenticated, IsActiveUser, HasAPIAccess]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_class = TerraformPlanFilter
    search_fields = ['config__name']
    ordering_fields = ['created_at', 'started_at', 'duration']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        return self.serializer_classes.get(self.action, self.serializer_classes['default'])
    
    def get_queryset(self):
        user = self.request.user
        
        if not user or not user.is_authenticated:
            return TerraformPlan.objects.none()
        
        if hasattr(user, 'role') and user.role in ['superadmin', 'admin']:
            return TerraformPlan.objects.all()
        
        return TerraformPlan.objects.filter(
            Q(executed_by=user) | Q(config__created_by=user) | Q(config__allowed_users=user)
        ).distinct()


# ============================================================================
# APPLICATIONS TERRAFORM (lecture seule)
# ============================================================================

class TerraformApplyViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet pour les applications Terraform (lecture seule)"""
    
    queryset = TerraformApply.objects.select_related('config', 'plan', 'executed_by').all()
    serializer_class = TerraformApplySerializer
    serializer_classes = {
        'retrieve': TerraformApplyDetailSerializer,
        'default': TerraformApplySerializer
    }
    
    permission_classes = [IsAuthenticated, IsActiveUser, HasAPIAccess]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_class = TerraformApplyFilter
    search_fields = ['config__name']
    ordering_fields = ['created_at', 'started_at', 'duration']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        return self.serializer_classes.get(self.action, self.serializer_classes['default'])
    
    def get_queryset(self):
        user = self.request.user
        
        if not user or not user.is_authenticated:
            return TerraformApply.objects.none()
        
        if hasattr(user, 'role') and user.role in ['superadmin', 'admin']:
            return TerraformApply.objects.all()
        
        return TerraformApply.objects.filter(
            Q(executed_by=user) | Q(config__created_by=user) | Q(config__allowed_users=user)
        ).distinct()


# ============================================================================
# ÉTATS TERRAFORM (lecture seule)
# ============================================================================

class TerraformStateViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet pour les états Terraform (lecture seule)"""
    
    queryset = TerraformState.objects.select_related('config', 'apply').all()
    serializer_class = TerraformStateSerializer
    serializer_classes = {
        'retrieve': TerraformStateDetailSerializer,
        'default': TerraformStateSerializer
    }
    
    permission_classes = [IsAuthenticated, IsActiveUser, HasAPIAccess]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_class = TerraformStateFilter
    search_fields = ['config__name']
    ordering_fields = ['captured_at', 'version']
    ordering = ['-captured_at']
    
    def get_serializer_class(self):
        return self.serializer_classes.get(self.action, self.serializer_classes['default'])
    
    def get_queryset(self):
        user = self.request.user
        
        if not user or not user.is_authenticated:
            return TerraformState.objects.none()
        
        if hasattr(user, 'role') and user.role in ['superadmin', 'admin']:
            return TerraformState.objects.all()
        
        return TerraformState.objects.filter(
            Q(config__created_by=user) | Q(config__allowed_users=user)
        ).distinct()


# ============================================================================
# MODULES TERRAFORM
# ============================================================================

class TerraformModuleViewSet(viewsets.ModelViewSet):
    """ViewSet pour les modules Terraform"""
    queryset = TerraformModule.objects.all()
    serializer_class = TerraformModuleSerializer
    permission_classes = [IsAuthenticated, IsActiveUser, HasAPIAccess]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_class = TerraformModuleFilter
    search_fields = ['name', 'namespace', 'description']
    ordering_fields = ['name', 'download_count', 'created_at']
    ordering = ['namespace', 'name']


# ============================================================================
# PROVIDERS TERRAFORM
# ============================================================================

class TerraformProviderViewSet(viewsets.ModelViewSet):
    """ViewSet pour les providers Terraform"""
    queryset = TerraformProvider.objects.all()
    serializer_class = TerraformProviderSerializer
    permission_classes = [IsAuthenticated, IsActiveUser, HasAPIAccess]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_class = TerraformProviderFilter
    search_fields = ['name', 'source']
    ordering_fields = ['name', 'version', 'created_at']
    ordering = ['name']


# ============================================================================
# VARIABLES TERRAFORM
# ============================================================================

class TerraformVariableViewSet(viewsets.ModelViewSet):
    """ViewSet pour les variables Terraform"""
    queryset = TerraformVariable.objects.select_related('config', 'created_by').all()
    serializer_class = TerraformVariableSerializer
    permission_classes = [IsAuthenticated, IsActiveUser, HasAPIAccess]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_class = TerraformVariableFilter
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    def get_queryset(self):
        user = self.request.user
        
        if not user or not user.is_authenticated:
            return TerraformVariable.objects.none()
        
        if hasattr(user, 'role') and user.role in ['superadmin', 'admin']:
            return TerraformVariable.objects.all()
        
        return TerraformVariable.objects.filter(
            Q(created_by=user) | Q(config__created_by=user) | Q(config__allowed_users=user)
        ).distinct()
    
    def perform_create(self, serializer):
        if self.request.user.is_authenticated:
            serializer.save(created_by=self.request.user)
        else:
            serializer.save()


# ============================================================================
# CREDENTIALS TERRAFORM
# ============================================================================

class TerraformCredentialViewSet(viewsets.ModelViewSet):
    """ViewSet pour les credentials Terraform"""
    queryset = TerraformCredential.objects.prefetch_related('configs').all()
    serializer_class = TerraformCredentialSerializer
    permission_classes = [IsAuthenticated, IsActiveUser, HasAPIAccess]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_class = TerraformCredentialFilter
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    def get_queryset(self):
        user = self.request.user
        
        if not user or not user.is_authenticated:
            return TerraformCredential.objects.none()
        
        if hasattr(user, 'role') and user.role in ['superadmin', 'admin']:
            return TerraformCredential.objects.all()
        
        return TerraformCredential.objects.filter(created_by=user)
    
    def perform_create(self, serializer):
        if self.request.user.is_authenticated:
            serializer.save(created_by=self.request.user)
        else:
            serializer.save()


# ============================================================================
# DASHBOARD TERRAFORM
# ============================================================================

class TerraformDashboardViewSet(viewsets.ViewSet):
    """Dashboard pour Terraform"""
    permission_classes = [IsAuthenticated, IsActiveUser, HasAPIAccess]
    
    def _get_user_querysets(self, user):
        is_admin = hasattr(user, 'role') and user.role in ['superadmin', 'admin']
        
        if is_admin:
            configs = TerraformConfig.objects.all()
            plans = TerraformPlan.objects.all()
            applies = TerraformApply.objects.all()
        else:
            configs = TerraformConfig.objects.filter(
                Q(created_by=user) | Q(allowed_users=user)
            )
            plans = TerraformPlan.objects.filter(
                Q(executed_by=user) | Q(config__created_by=user) | Q(config__allowed_users=user)
            )
            applies = TerraformApply.objects.filter(
                Q(executed_by=user) | Q(config__created_by=user) | Q(config__allowed_users=user)
            )
        
        return configs, plans, applies
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Résumé des activités Terraform"""
        user = request.user
        
        if not user or not user.is_authenticated:
            return error_response("Authentication required")
        
        configs, plans, applies = self._get_user_querysets(user)
        
        last_24h = timezone.now() - timedelta(hours=24)
        plans_24h = plans.filter(created_at__gte=last_24h)
        applies_24h = applies.filter(created_at__gte=last_24h)
        
        successful_applies = applies_24h.filter(status='completed', return_code=0).count()
        total_applies = applies_24h.count()
        success_rate = (successful_applies / total_applies * 100) if total_applies > 0 else 0
        
        # Récupérer les ressources gérées (depuis les états récents)
        resources_managed = 0
        latest_states = TerraformState.objects.filter(
            config__in=configs
        ).order_by('config', '-version').distinct('config')
        
        for state in latest_states:
            resources_managed += state.resources_count
        
        data = {
            'statistics': {
                'total_configs': configs.count(),
                'active_configs': configs.filter(status='active').count(),
                'total_modules': TerraformModule.objects.count(),
                'total_credentials': TerraformCredential.objects.filter(
                    Q(created_by=user) | Q(configs__in=configs)
                ).distinct().count() if not hasattr(user, 'role') or user.role not in ['superadmin', 'admin'] else TerraformCredential.objects.count(),
                'plans_24h': plans_24h.count(),
                'applies_24h': total_applies,
                'success_rate_24h': round(success_rate, 2),
                'resources_managed': resources_managed
            },
            'recent_activities': self._get_recent_activities(plans, applies),
            'top_configs': self._get_top_configs(configs),
            'providers_summary': self._get_providers_summary(configs)
        }
        
        return success_response(data, "Dashboard summary retrieved")
    
    def _get_recent_activities(self, plans, applies, limit=10):
        """Récupère les activités récentes (plans et applies)"""
        activities = []
        
        for plan in plans.order_by('-created_at')[:limit//2]:
            activities.append({
                'id': str(plan.id),
                'type': 'plan',
                'config_name': plan.config.name,
                'status': plan.status,
                'created_at': plan.created_at,
                'executed_by': plan.executed_by.get_full_name() if plan.executed_by else None
            })
        
        for apply in applies.order_by('-created_at')[:limit//2]:
            activities.append({
                'id': str(apply.id),
                'type': 'apply',
                'config_name': apply.config.name,
                'status': apply.status,
                'created_at': apply.created_at,
                'executed_by': apply.executed_by.get_full_name() if apply.executed_by else None
            })
        
        # Trier par date décroissante
        activities.sort(key=lambda x: x['created_at'], reverse=True)
        return activities[:limit]
    
    def _get_top_configs(self, configs, limit=5):
        """Récupère les configurations les plus utilisées"""
        return [
            {
                'id': str(c.id),
                'name': c.name,
                'apply_count': c.apply_count,
                'provider': c.get_provider_display(),
                'last_apply_at': c.last_apply_at
            }
            for c in configs.order_by('-apply_count')[:limit]
        ]
    
    def _get_providers_summary(self, configs):
        """Récupère le résumé des providers utilisés"""
        providers = {}
        for config in configs:
            provider = config.provider
            providers[provider] = providers.get(provider, 0) + 1
        
        return [
            {'provider': provider, 'count': count}
            for provider, count in providers.items()
        ]