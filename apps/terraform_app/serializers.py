"""
Terraform App Serializers - API serializers professionnels
"""
from rest_framework import serializers
from django.utils import timezone
from .models import (
    TerraformConfig, TerraformPlan, TerraformApply, TerraformState,
    TerraformModule, TerraformProvider, TerraformVariable, TerraformCredential
)
from apps.inventory.models import Site, Cluster, Tenant
import json


# ============================================================================
# CONFIGURATIONS TERRAFORM
# ============================================================================

class TerraformConfigSerializer(serializers.ModelSerializer):
    """Serializer de base pour les configurations Terraform"""
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True, allow_null=True)
    site_name = serializers.CharField(source='site.name', read_only=True, allow_null=True)
    cluster_name = serializers.CharField(source='cluster.name', read_only=True, allow_null=True)
    tenant_name = serializers.CharField(source='tenant.name', read_only=True, allow_null=True)
    provider_display = serializers.CharField(source='get_provider_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = TerraformConfig
        fields = [
            'id', 'name', 'description', 'provider', 'provider_display', 'provider_version',
            'main_tf', 'variables_tf', 'outputs_tf', 'terraform_tfvars',
            'config_files', 'variables', 'backend_type', 'backend_config',
            'version', 'status', 'status_display',
            'apply_count', 'last_apply_status', 'last_apply_at',
            'site', 'site_name', 'cluster', 'cluster_name', 'tenant', 'tenant_name',
            'created_by', 'created_by_name', 'allowed_users',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'created_by',
            'apply_count', 'last_apply_status', 'last_apply_at'
        ]
    
    def validate_main_tf(self, value):
        """Valide que main.tf n'est pas vide"""
        if not value or not value.strip():
            raise serializers.ValidationError("main.tf configuration is required")
        return value
    
    def validate_variables(self, value):
        """Valide la structure des variables"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Variables must be a dictionary")
        
        for var_name, var_config in value.items():
            if not isinstance(var_config, dict):
                raise serializers.ValidationError(f"Variable '{var_name}' must be a dictionary")
            
            if 'type' not in var_config:
                var_config['type'] = 'string'
            
            valid_types = ['string', 'number', 'bool', 'list', 'map', 'object']
            if var_config.get('type') not in valid_types:
                raise serializers.ValidationError(
                    f"Variable '{var_name}' type must be one of: {', '.join(valid_types)}"
                )
        
        return value


class TerraformConfigDetailSerializer(TerraformConfigSerializer):
    """Serializer détaillé pour les configurations Terraform"""
    plans = serializers.SerializerMethodField()
    applies = serializers.SerializerMethodField()
    states = serializers.SerializerMethodField()
    credentials = serializers.SerializerMethodField()
    variables_list = serializers.SerializerMethodField()
    
    class Meta(TerraformConfigSerializer.Meta):
        fields = TerraformConfigSerializer.Meta.fields + [
            'plans', 'applies', 'states', 'credentials', 'variables_list'
        ]
    
    def get_plans(self, obj):
        """Retourne les derniers plans"""
        plans = obj.plans.order_by('-created_at')[:5]
        return [{
            'id': str(p.id),
            'status': p.status,
            'has_changes': p.has_changes,
            'resources_add': p.resources_add,
            'resources_change': p.resources_change,
            'resources_destroy': p.resources_destroy,
            'created_at': p.created_at.isoformat() if p.created_at else None
        } for p in plans]
    
    def get_applies(self, obj):
        """Retourne les dernières applications"""
        applies = obj.applies.order_by('-created_at')[:5]
        return [{
            'id': str(a.id),
            'status': a.status,
            'return_code': a.return_code,
            'created_at': a.created_at.isoformat() if a.created_at else None,
            'executed_by': a.executed_by.get_full_name() if a.executed_by else None
        } for a in applies]
    
    def get_states(self, obj):
        """Retourne les derniers états"""
        states = obj.states.order_by('-captured_at')[:3]
        return [{
            'id': str(s.id),
            'version': s.version,
            'resources_count': s.resources_count,
            'captured_at': s.captured_at.isoformat() if s.captured_at else None
        } for s in states]
    
    def get_credentials(self, obj):
        """Retourne les credentials associés"""
        return [{'id': str(c.id), 'name': c.name, 'provider': c.provider} 
                for c in obj.credentials.all()]
    
    def get_variables_list(self, obj):
        """Retourne les variables stockées"""
        variables = obj.stored_variables.all()
        return [{
            'id': str(v.id),
            'name': v.name,
            'environment': v.environment,
            'is_sensitive': v.is_sensitive
        } for v in variables]


# ============================================================================
# PLANS TERRAFORM
# ============================================================================

class TerraformPlanSerializer(serializers.ModelSerializer):
    """Serializer pour les plans Terraform"""
    config_name = serializers.CharField(source='config.name', read_only=True)
    executed_by_name = serializers.CharField(source='executed_by.get_full_name', read_only=True, allow_null=True)
    duration_display = serializers.SerializerMethodField()
    
    class Meta:
        model = TerraformPlan
        fields = [
            'id', 'config', 'config_name', 'plan_id', 'plan_file', 'plan_json',
            'resources_add', 'resources_change', 'resources_destroy',
            'status', 'has_changes',
            'executed_by', 'executed_by_name', 'started_at', 'completed_at',
            'duration', 'duration_display', 'stdout', 'stderr', 'return_code',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'started_at', 'completed_at',
            'duration', 'stdout', 'stderr', 'return_code', 'plan_json'
        ]
    
    def get_duration_display(self, obj):
        """Formatage lisible de la durée"""
        if obj.duration:
            if obj.duration < 60:
                return f"{obj.duration:.1f}s"
            elif obj.duration < 3600:
                return f"{obj.duration/60:.1f}m"
            else:
                return f"{obj.duration/3600:.1f}h"
        return None


class TerraformPlanDetailSerializer(TerraformPlanSerializer):
    """Serializer détaillé pour les plans"""
    
    class Meta(TerraformPlanSerializer.Meta):
        fields = TerraformPlanSerializer.Meta.fields
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        
        # Ajouter un résumé formaté
        if instance.plan_json:
            data['summary'] = {
                'resources': {
                    'add': instance.resources_add,
                    'change': instance.resources_change,
                    'destroy': instance.resources_destroy,
                    'total': instance.resources_add + instance.resources_change + instance.resources_destroy
                }
            }
        
        return data


# ============================================================================
# APPLICATIONS TERRAFORM
# ============================================================================

class TerraformApplySerializer(serializers.ModelSerializer):
    """Serializer pour les applications Terraform"""
    config_name = serializers.CharField(source='config.name', read_only=True)
    plan_id = serializers.CharField(source='plan.plan_id', read_only=True, allow_null=True)
    executed_by_name = serializers.CharField(source='executed_by.get_full_name', read_only=True, allow_null=True)
    duration_display = serializers.SerializerMethodField()
    
    class Meta:
        model = TerraformApply
        fields = [
            'id', 'config', 'config_name', 'plan', 'plan_id', 'apply_id',
            'status', 'executed_by', 'executed_by_name',
            'started_at', 'completed_at', 'duration', 'duration_display',
            'stdout', 'stderr', 'return_code', 'state_json', 'outputs',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'started_at', 'completed_at',
            'duration', 'stdout', 'stderr', 'return_code', 'state_json', 'outputs'
        ]
    
    def get_duration_display(self, obj):
        """Formatage lisible de la durée"""
        if obj.duration:
            if obj.duration < 60:
                return f"{obj.duration:.1f}s"
            elif obj.duration < 3600:
                return f"{obj.duration/60:.1f}m"
            else:
                return f"{obj.duration/3600:.1f}h"
        return None


class TerraformApplyDetailSerializer(TerraformApplySerializer):
    """Serializer détaillé pour les applications"""
    
    class Meta(TerraformApplySerializer.Meta):
        fields = TerraformApplySerializer.Meta.fields
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        
        # Ajouter les outputs formatés
        if instance.outputs:
            data['outputs_formatted'] = {
                name: {
                    'value': output.get('value'),
                    'type': output.get('type'),
                    'sensitive': output.get('sensitive', False)
                }
                for name, output in instance.outputs.items()
            }
        
        return data


# ============================================================================
# ÉTATS TERRAFORM
# ============================================================================

class TerraformStateSerializer(serializers.ModelSerializer):
    """Serializer pour les états Terraform"""
    config_name = serializers.CharField(source='config.name', read_only=True)
    apply_id = serializers.CharField(source='apply.apply_id', read_only=True, allow_null=True)
    
    class Meta:
        model = TerraformState
        fields = [
            'id', 'config', 'config_name', 'apply', 'apply_id',
            'state_file', 'state_json', 'version', 'lineage', 'serial',
            'resources_count', 'resources_summary', 'captured_at',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'captured_at',
            'resources_count', 'resources_summary'
        ]


class TerraformStateDetailSerializer(TerraformStateSerializer):
    """Serializer détaillé pour les états"""
    
    class Meta(TerraformStateSerializer.Meta):
        fields = TerraformStateSerializer.Meta.fields
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        
        # Ajouter le résumé des ressources
        if instance.resources_summary:
            data['resources_by_type'] = instance.resources_summary.get('by_type', {})
            data['resources_by_provider'] = instance.resources_summary.get('by_provider', {})
        
        return data


# ============================================================================
# MODULES TERRAFORM
# ============================================================================

class TerraformModuleSerializer(serializers.ModelSerializer):
    """Serializer pour les modules Terraform"""
    source_display = serializers.CharField(source='get_source_display', read_only=True)
    
    class Meta:
        model = TerraformModule
        fields = [
            'id', 'name', 'namespace', 'version', 'source', 'source_display',
            'source_url', 'source_version', 'description', 'documentation',
            'module_path', 'readme', 'input_variables', 'output_variables',
            'required_providers', 'download_count', 'used_in_configs',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'download_count', 'used_in_configs'
        ]


# ============================================================================
# PROVIDERS TERRAFORM
# ============================================================================

class TerraformProviderSerializer(serializers.ModelSerializer):
    """Serializer pour les providers Terraform"""
    
    class Meta:
        model = TerraformProvider
        fields = [
            'id', 'name', 'version', 'source', 'config_schema',
            'default_config', 'documentation_url', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


# ============================================================================
# VARIABLES TERRAFORM
# ============================================================================

class TerraformVariableSerializer(serializers.ModelSerializer):
    """Serializer pour les variables Terraform"""
    config_name = serializers.CharField(source='config.name', read_only=True, allow_null=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True, allow_null=True)
    
    class Meta:
        model = TerraformVariable
        fields = [
            'id', 'config', 'config_name', 'name', 'value', 'description',
            'is_sensitive', 'encrypted_value', 'environment',
            'created_by', 'created_by_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by']
        extra_kwargs = {
            'value': {'write_only': False},
            'encrypted_value': {'write_only': True},
        }
    
    def validate(self, data):
        """Validation personnalisée"""
        if data.get('is_sensitive') and not data.get('encrypted_value'):
            # Si sensible, on peut stocker dans encrypted_value
            data['encrypted_value'] = str(data.get('value', ''))
            data['value'] = None
        return data


# ============================================================================
# CREDENTIALS TERRAFORM
# ============================================================================

class TerraformCredentialSerializer(serializers.ModelSerializer):
    """Serializer pour les credentials Terraform"""
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True, allow_null=True)
    provider_display = serializers.CharField(source='get_provider_display', read_only=True)
    configs_count = serializers.IntegerField(source='configs.count', read_only=True)
    
    class Meta:
        model = TerraformCredential
        fields = [
            'id', 'name', 'provider', 'provider_display', 'description',
            'access_key', 'secret_key', 'token',
            'aws_profile', 'aws_region',
            'azure_subscription_id', 'azure_tenant_id', 'azure_client_id', 'azure_client_secret',
            'gcp_project', 'gcp_service_account',
            'ssh_user', 'ssh_private_key', 'ssh_key_passphrase',
            'configs', 'configs_count',
            'created_by', 'created_by_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by', 'configs_count']
        extra_kwargs = {
            'access_key': {'write_only': True},
            'secret_key': {'write_only': True},
            'token': {'write_only': True},
            'azure_client_secret': {'write_only': True},
            'gcp_service_account': {'write_only': True},
            'ssh_private_key': {'write_only': True},
            'ssh_key_passphrase': {'write_only': True},
        }


# ============================================================================
# REQUESTS
# ============================================================================

class TerraformPlanRequestSerializer(serializers.Serializer):
    """Serializer pour les requêtes de plan"""
    var_file = serializers.CharField(required=False, allow_blank=True, help_text="Path to variables file")
    out_file = serializers.CharField(required=False, allow_blank=True, help_text="Path to save plan file")
    target = serializers.CharField(required=False, allow_blank=True, help_text="Target resource address")


class TerraformApplyRequestSerializer(serializers.Serializer):
    """Serializer pour les requêtes d'application"""
    plan_id = serializers.UUIDField(required=False, allow_null=True, help_text="ID of saved plan")
    plan_file = serializers.CharField(required=False, allow_blank=True, help_text="Path to plan file")
    auto_approve = serializers.BooleanField(default=False, help_text="Skip approval prompt")
    target = serializers.CharField(required=False, allow_blank=True, help_text="Target resource address")


class TerraformDestroyRequestSerializer(serializers.Serializer):
    """Serializer pour les requêtes de destruction"""
    auto_approve = serializers.BooleanField(default=False, help_text="Skip approval prompt")
    target = serializers.CharField(required=False, allow_blank=True, help_text="Target resource address")


class TerraformVariableRequestSerializer(serializers.Serializer):
    """Serializer pour définir des variables"""
    name = serializers.CharField(required=True)
    value = serializers.JSONField(required=True)
    description = serializers.CharField(required=False, allow_blank=True)
    is_sensitive = serializers.BooleanField(default=False)
    environment = serializers.CharField(required=False, allow_blank=True)


# ============================================================================
# DASHBOARD
# ============================================================================

class TerraformDashboardStatsSerializer(serializers.Serializer):
    """Serializer pour les statistiques du dashboard"""
    total_configs = serializers.IntegerField()
    active_configs = serializers.IntegerField()
    total_modules = serializers.IntegerField()
    total_credentials = serializers.IntegerField()
    plans_24h = serializers.IntegerField()
    applies_24h = serializers.IntegerField()
    success_rate_24h = serializers.FloatField()
    resources_managed = serializers.IntegerField()


class TerraformRecentActivitySerializer(serializers.Serializer):
    """Serializer pour les activités récentes"""
    id = serializers.UUIDField()
    type = serializers.CharField()  # 'plan', 'apply', 'state'
    config_name = serializers.CharField()
    status = serializers.CharField()
    created_at = serializers.DateTimeField()
    executed_by = serializers.CharField(allow_null=True)


class TerraformTopConfigSerializer(serializers.Serializer):
    """Serializer pour les configurations les plus utilisées"""
    id = serializers.UUIDField()
    name = serializers.CharField()
    apply_count = serializers.IntegerField()
    provider = serializers.CharField()
    last_apply_at = serializers.DateTimeField(allow_null=True)


class TerraformDashboardSerializer(serializers.Serializer):
    """Serializer pour le dashboard Terraform"""
    statistics = TerraformDashboardStatsSerializer()
    recent_activities = TerraformRecentActivitySerializer(many=True)
    top_configs = TerraformTopConfigSerializer(many=True)
    providers_summary = serializers.ListField(child=serializers.DictField())