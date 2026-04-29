# apps/ansible_app/serializers.py
"""
Ansible App Serializers - API serializers professionnels
Version corrigée pour Swagger/OpenAPI
"""
from rest_framework import serializers
from django.utils import timezone
from .models import *
from .validators import validate_playbook_content, validate_inventory_content


# ============================================================================
# INVENTAIRES
# ============================================================================

class AnsibleInventorySerializer(serializers.ModelSerializer):
    """Serializer de base pour les inventaires"""
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    hosts_count = serializers.IntegerField(source='get_hosts_count', read_only=True)
    devices_count = serializers.IntegerField(source='devices.count', read_only=True)
    sites_count = serializers.IntegerField(source='sites.count', read_only=True)
    
    class Meta:
        model = AnsibleInventory
        fields = [
            'id', 'name', 'description', 'inventory_type', 'format',
            'content', 'variables', 'source_script', 'source_url',
            'devices', 'sites', 'clusters', 'tenants', 'device_filters',
            'vars_file', 'is_active', 'created_by', 'created_by_name',
            'created_at', 'updated_at', 'hosts_count', 'devices_count',
            'sites_count'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by', 
                           'hosts_count', 'devices_count', 'sites_count']
    
    def validate_content(self, value):
        """Valide le contenu de l'inventaire"""
        if self.initial_data.get('inventory_type') == 'static' and value:
            result = validate_inventory_content(value, self.initial_data.get('format', 'ini'))
            if not result['valid']:
                raise serializers.ValidationError(result['message'])
        return value


class AnsibleInventoryDetailSerializer(AnsibleInventorySerializer):
    """Serializer détaillé pour les inventaires"""
    generated_content = serializers.SerializerMethodField()
    playbooks = serializers.SerializerMethodField()
    devices_details = serializers.SerializerMethodField()
    sites_details = serializers.SerializerMethodField()
    
    class Meta(AnsibleInventorySerializer.Meta):
        fields = AnsibleInventorySerializer.Meta.fields + [
            'generated_content', 'playbooks', 'devices_details', 'sites_details'
        ]
    
    def get_generated_content(self, obj):
        """Génère le contenu de l'inventaire"""
        return obj.generate_inventory_content()
    
    def get_playbooks(self, obj):
        """Retourne les playbooks associés (format simplifié)"""
        return [{'id': str(p.id), 'name': p.name} for p in obj.playbooks.all()]
    
    def get_devices_details(self, obj):
        """Retourne les détails des devices associés"""
        devices = obj.devices.all()[:10]  # Limiter à 10 pour la performance
        return [{'id': str(d.id), 'hostname': d.hostname, 'management_ip': d.management_ip} 
                for d in devices]
    
    def get_sites_details(self, obj):
        """Retourne les détails des sites associés"""
        sites = obj.sites.all()
        return [{'id': str(s.id), 'name': s.name} for s in sites]


# ============================================================================
# PLAYBOOKS
# ============================================================================

class PlaybookSerializer(serializers.ModelSerializer):
    """Serializer de base pour les playbooks"""
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    inventory_name = serializers.CharField(source='inventory.name', read_only=True, allow_null=True)
    default_inventory_name = serializers.CharField(source='default_inventory.name', read_only=True, allow_null=True)
    success_rate = serializers.FloatField(read_only=True)
    last_execution = serializers.SerializerMethodField()
    
    class Meta:
        model = Playbook
        fields = [
            'id', 'name', 'description', 'content', 'requirements',
            'playbook_file', 'vars_file', 'inventory', 'default_inventory',
            'inventory_name', 'default_inventory_name', 'timeout', 'forks',
            'tags', 'status', 'visibility', 'version', 'execution_count',
            'success_count', 'failure_count', 'avg_duration', 'success_rate',
            'created_by', 'created_by_name', 'created_at', 'updated_at',
            'last_execution', 'allowed_users'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'created_by',
            'execution_count', 'success_count', 'failure_count', 
            'avg_duration', 'success_rate'
        ]
    
    def get_last_execution(self, obj):
        """Retourne la dernière exécution (format simplifié)"""
        execution = obj.executions.order_by('-created_at').first()
        if execution:
            return {
                'id': str(execution.id),
                'status': execution.status,
                'created_at': execution.created_at.isoformat() if execution.created_at else None,
                'success': execution.status == 'completed'
            }
        return None
    
    def validate_content(self, value):
        """Valide le contenu du playbook"""
        result = validate_playbook_content(value)
        if not result['valid']:
            raise serializers.ValidationError(result['message'])
        return value


# apps/ansible_app/serializers.py

class PlaybookDetailSerializer(PlaybookSerializer):
    """Serializer détaillé pour les playbooks"""
    executions = serializers.SerializerMethodField()
    roles = serializers.SerializerMethodField()
    collections = serializers.SerializerMethodField()
    tasks = serializers.SerializerMethodField()
    credentials = serializers.SerializerMethodField()
    
    class Meta(PlaybookSerializer.Meta):
        fields = PlaybookSerializer.Meta.fields + [
            'executions', 'roles', 'collections', 'tasks', 'credentials'
        ]
    
    def get_executions(self, obj):
        executions = obj.executions.order_by('-created_at')[:5]
        return [{
            'id': str(e.id),
            'status': e.status,
            'created_at': e.created_at.isoformat() if e.created_at else None,
            'duration': e.duration,
            'executed_by': e.executed_by.get_full_name() if e.executed_by else None
        } for e in executions]
    
    def get_roles(self, obj):
        return [{'id': str(r.id), 'name': str(r)} for r in obj.roles.all()]
    
    def get_collections(self, obj):
        return [{'id': str(c.id), 'name': str(c)} for c in obj.collections.all()]
    
    def get_tasks(self, obj):
        return [{'id': str(t.id), 'name': t.name} for t in obj.tasks.all()]
    
    def get_credentials(self, obj):
        return [{'id': str(c.id), 'name': c.name, 'type': c.credential_type} 
                for c in obj.credentials.all()]


# ============================================================================
# EXÉCUTIONS
# ============================================================================

# apps/ansible_app/serializers.py

class PlaybookExecutionSerializer(serializers.ModelSerializer):
    """Serializer de base pour les exécutions"""
    playbook_name = serializers.CharField(source='playbook.name', read_only=True)
    inventory_name = serializers.CharField(source='inventory.name', read_only=True, allow_null=True)
    executed_by_name = serializers.CharField(source='executed_by.get_full_name', read_only=True, allow_null=True)
    duration_display = serializers.SerializerMethodField()
    
    class Meta:
        model = PlaybookExecution
        fields = [
            'id', 'playbook', 'playbook_name', 'inventory', 'inventory_name',
            'inventory_snapshot', 'extra_vars', 'limit', 'tags', 'skip_tags',
            'check_mode', 'diff_mode', 'status', 'output', 'error_output',
            'summary', 'facts', 'started_at', 'completed_at', 'duration',
            'duration_display', 'executed_by', 'executed_by_name',
            'execution_host', 'command', 'return_code', 'host_results',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'started_at', 'completed_at',
            'duration', 'output', 'error_output', 'summary', 'facts',
            'return_code', 'command', 'inventory_snapshot', 'host_results'
        ]
    
    def get_duration_display(self, obj):
        if obj.duration:
            if obj.duration < 60:
                return f"{obj.duration:.1f}s"
            elif obj.duration < 3600:
                return f"{obj.duration/60:.1f}m"
            else:
                return f"{obj.duration/3600:.1f}h"
        return None


class PlaybookExecutionDetailSerializer(PlaybookExecutionSerializer):
    """Serializer détaillé pour les exécutions"""
    
    class Meta(PlaybookExecutionSerializer.Meta):
        fields = PlaybookExecutionSerializer.Meta.fields
    
    def to_representation(self, instance):
        """Ajoute des informations supplémentaires"""
        data = super().to_representation(instance)
        
        # Ajouter un résumé formaté
        if instance.summary:
            data['summary_formatted'] = {
                'ok': instance.summary.get('ok', 0),
                'changed': instance.summary.get('changed', 0),
                'failed': instance.summary.get('failed', 0),
                'unreachable': instance.summary.get('unreachable', 0),
                'skipped': instance.summary.get('skipped', 0),
                'rescued': instance.summary.get('rescued', 0),
                'ignored': instance.summary.get('ignored', 0),
            }
        
        return data


# ============================================================================
# PLANIFICATIONS
# ============================================================================

class PlaybookScheduleSerializer(serializers.ModelSerializer):
    """Serializer pour les planifications"""
    playbook_name = serializers.CharField(source='playbook.name', read_only=True)
    inventory_name = serializers.CharField(source='inventory.name', read_only=True, allow_null=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True, allow_null=True)
    last_execution_status = serializers.SerializerMethodField()
    next_run_formatted = serializers.SerializerMethodField()
    
    class Meta:
        model = PlaybookSchedule
        fields = [
            'id', 'name', 'playbook', 'playbook_name', 'inventory', 'inventory_name',
            'schedule_type', 'cron_expression', 'start_date', 'end_date',
            'last_run', 'next_run', 'next_run_formatted', 'extra_vars', 'limit',
            'tags', 'check_mode', 'status', 'notify_on_success', 'notify_on_failure',
            'notification_emails', 'execution_count', 'last_execution',
            'last_execution_status', 'created_by', 'created_by_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'created_by',
            'last_run', 'next_run', 'execution_count'
        ]
    
    def get_last_execution_status(self, obj):
        """Statut de la dernière exécution"""
        if obj.last_execution:
            return {
                'id': str(obj.last_execution.id),
                'status': obj.last_execution.status,
                'success': obj.last_execution.status == 'completed',
                'created_at': obj.last_execution.created_at.isoformat() if obj.last_execution.created_at else None
            }
        return None
    
    def get_next_run_formatted(self, obj):
        """Formatage de la prochaine exécution"""
        if obj.next_run:
            return {
                'datetime': obj.next_run.isoformat(),
                'humanized': self._humanize_datetime(obj.next_run)
            }
        return None
    
    def _humanize_datetime(self, dt):
        """Humanise une date"""
        from django.utils.timesince import timesince
        return f"in {timesince(dt)}" if dt > timezone.now() else "past due"
    
    def validate(self, data):
        """Validation de la planification"""
        if data.get('schedule_type') == 'cron' and not data.get('cron_expression'):
            raise serializers.ValidationError({
                'cron_expression': 'Cron expression required for cron schedule type'
            })
        
        if data.get('start_date') and data['start_date'] < timezone.now():
            raise serializers.ValidationError({
                'start_date': 'Start date must be in the future'
            })
        
        return data


# ============================================================================
# RÔLES
# ============================================================================

class AnsibleRoleSerializer(serializers.ModelSerializer):
    """Serializer pour les rôles Ansible"""
    playbooks_count = serializers.IntegerField(source='playbooks.count', read_only=True)
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = AnsibleRole
        fields = [
            'id', 'name', 'namespace', 'full_name', 'version', 'source',
            'source_url', 'source_version', 'description', 'documentation',
            'license', 'role_path', 'readme', 'dependencies', 'playbooks',
            'playbooks_count', 'download_count', 'used_in_playbooks',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'download_count', 
            'used_in_playbooks', 'playbooks_count'
        ]
    
    def get_full_name(self, obj):
        return f"{obj.namespace}.{obj.name}"

# ============================================================================
# COLLECTIONS
# ============================================================================

class AnsibleCollectionSerializer(serializers.ModelSerializer):
    """Serializer pour les collections Ansible"""
    playbooks_count = serializers.IntegerField(source='playbooks.count', read_only=True)
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = AnsibleCollection
        fields = [
            'id', 'name', 'namespace', 'full_name', 'version', 'description',
            'documentation', 'dependencies', 'installed_path', 'installed_at',
            'playbooks', 'playbooks_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'installed_at', 'playbooks_count']
    
    def get_full_name(self, obj):
        return f"{obj.namespace}.{obj.name}"


# ============================================================================
# TÂCHES
# ============================================================================

class AnsibleTaskSerializer(serializers.ModelSerializer):
    """Serializer pour les tâches Ansible"""
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True, allow_null=True)
    playbooks_count = serializers.IntegerField(source='playbooks.count', read_only=True)
    
    class Meta:
        model = AnsibleTask
        fields = [
            'id', 'name', 'description', 'content', 'tags', 'playbooks',
            'playbooks_count', 'created_by', 'created_by_name', 'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'playbooks_count']


# ============================================================================
# VARIABLES
# ============================================================================

class AnsibleVarsSerializer(serializers.ModelSerializer):
    """Serializer pour les variables Ansible"""
    tenant_name = serializers.CharField(source='tenant.name', read_only=True, allow_null=True)
    inventory_name = serializers.CharField(source='inventory.name', read_only=True, allow_null=True)
    playbook_name = serializers.CharField(source='playbook.name', read_only=True, allow_null=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True, allow_null=True)
    
    class Meta:
        model = AnsibleVars
        fields = [
            'id', 'name', 'description', 'variables', 'inventory',
            'inventory_name', 'playbook', 'playbook_name', 'tenant',
            'tenant_name', 'created_by', 'created_by_name', 'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


# ============================================================================
# CREDENTIALS
# ============================================================================

class AnsibleCredentialSerializer(serializers.ModelSerializer):
    """Serializer pour les credentials Ansible"""
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True, allow_null=True)
    playbooks_count = serializers.IntegerField(source='playbooks.count', read_only=True)
    inventories_count = serializers.IntegerField(source='inventories.count', read_only=True)
    
    class Meta:
        model = AnsibleCredential
        fields = [
            'id', 'name', 'credential_type', 'description', 'username',
            'password', 'ssh_key', 'ssh_key_passphrase', 'vault_password',
            'access_key', 'secret_key', 'playbooks', 'playbooks_count',
            'inventories', 'inventories_count', 'created_by', 'created_by_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'playbooks_count', 'inventories_count']
        extra_kwargs = {
            'password': {'write_only': True},
            'ssh_key': {'write_only': True},
            'ssh_key_passphrase': {'write_only': True},
            'vault_password': {'write_only': True},
            'access_key': {'write_only': True},
            'secret_key': {'write_only': True},
        }


# ============================================================================
# REQUESTS
# ============================================================================

class ExecutePlaybookRequestSerializer(serializers.Serializer):
    """Serializer pour les requêtes d'exécution de playbook"""
    extra_vars = serializers.JSONField(required=False, default=dict)
    limit = serializers.CharField(required=False, allow_blank=True, default='')
    tags = serializers.ListField(
        child=serializers.CharField(), 
        required=False, 
        default=list,
        allow_empty=True
    )
    skip_tags = serializers.ListField(
        child=serializers.CharField(), 
        required=False, 
        default=list,
        allow_empty=True
    )
    check_mode = serializers.BooleanField(required=False, default=False)
    diff_mode = serializers.BooleanField(required=False, default=False)
    inventory_id = serializers.UUIDField(required=False, allow_null=True)


class AdHocCommandSerializer(serializers.Serializer):
    """Serializer pour commandes ad-hoc"""
    hosts = serializers.CharField(required=True, help_text="Host pattern (e.g., 'all', 'webservers')")
    module = serializers.CharField(required=True, help_text="Ansible module name (e.g., 'ping', 'shell')")
    args = serializers.CharField(required=True, allow_blank=True, help_text="Module arguments")
    inventory_content = serializers.CharField(required=True, help_text="Inventory content in INI format")


class GenerateInventorySerializer(serializers.Serializer):
    """Serializer pour génération d'inventaire"""
    device_ids = serializers.ListField(
        child=serializers.UUIDField(), 
        required=False, 
        default=list,
        help_text="List of device UUIDs"
    )
    site_ids = serializers.ListField(
        child=serializers.UUIDField(), 
        required=False, 
        default=list,
        help_text="List of site UUIDs"
    )
    cluster_ids = serializers.ListField(
        child=serializers.UUIDField(), 
        required=False, 
        default=list,
        help_text="List of cluster UUIDs"
    )
    tenant_ids = serializers.ListField(
        child=serializers.UUIDField(), 
        required=False, 
        default=list,
        help_text="List of tenant UUIDs"
    )
    format = serializers.ChoiceField(
        choices=['ini', 'yaml', 'json'], 
        default='ini',
        help_text="Inventory format"
    )
    variables = serializers.JSONField(
        required=False, 
        default=dict,
        help_text="Global variables for the inventory"
    )


# ============================================================================
# DASHBOARD
# ============================================================================

class DashboardStatisticsSerializer(serializers.Serializer):
    """Serializer pour les statistiques du dashboard"""
    total_playbooks = serializers.IntegerField()
    active_playbooks = serializers.IntegerField()
    total_inventories = serializers.IntegerField()
    total_schedules = serializers.IntegerField()
    executions_24h = serializers.IntegerField()
    successful_24h = serializers.IntegerField()
    failed_24h = serializers.IntegerField()
    success_rate_24h = serializers.FloatField()
    avg_duration_24h = serializers.FloatField()


class RecentExecutionItemSerializer(serializers.Serializer):
    """Serializer pour un élément d'exécution récente"""
    id = serializers.UUIDField()
    playbook_name = serializers.CharField()
    status = serializers.CharField()
    created_at = serializers.DateTimeField()
    executed_by = serializers.CharField(allow_null=True)


class TopPlaybookItemSerializer(serializers.Serializer):
    """Serializer pour un élément de top playbook"""
    id = serializers.UUIDField()
    name = serializers.CharField()
    execution_count = serializers.IntegerField()
    success_rate = serializers.FloatField()


class UpcomingScheduleItemSerializer(serializers.Serializer):
    """Serializer pour un élément de planification à venir"""
    id = serializers.UUIDField()
    name = serializers.CharField()
    playbook_name = serializers.CharField()
    next_run = serializers.DateTimeField()
    schedule_type = serializers.CharField()


class AnsibleDashboardSerializer(serializers.Serializer):
    """Serializer pour le dashboard Ansible"""
    statistics = DashboardStatisticsSerializer()
    recent_executions = RecentExecutionItemSerializer(many=True)
    top_playbooks = TopPlaybookItemSerializer(many=True)
    upcoming_schedules = UpcomingScheduleItemSerializer(many=True)
    
    class Meta:
        fields = ['statistics', 'recent_executions', 'top_playbooks', 'upcoming_schedules']