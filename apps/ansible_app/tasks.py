# apps/ansible_app/tasks.py
"""
Ansible App Tasks - Tâches Celery pour exécution asynchrone
"""
from celery import shared_task
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Q
import logging
import json
import traceback

from .models import PlaybookExecution, PlaybookSchedule, AnsibleInventory
from .executor import AnsibleExecutor

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def execute_playbook_task(self, execution_id):
    """
    Tâche asynchrone pour exécuter un playbook
    
    Args:
        execution_id (str): ID de l'exécution
        
    Returns:
        dict: Résultat de l'exécution
    """
    logger.info(f"Starting playbook execution task for ID: {execution_id}")
    
    try:
        # Récupérer l'exécution
        execution = PlaybookExecution.objects.get(id=execution_id)
        
        # Mettre à jour le statut
        execution.status = 'running'
        execution.started_at = timezone.now()
        execution.save(update_fields=['status', 'started_at'])
        
        logger.info(f"Execution {execution_id} started for playbook: {execution.playbook.name}")
        
        # Préparer l'exécuteur
        executor = AnsibleExecutor(execution=execution)
        
        # Déterminer l'inventaire à utiliser
        inventory = execution.inventory or execution.playbook.inventory
        
        if not inventory:
            raise ValueError("No inventory specified for execution")
        
        # Obtenir le contenu de l'inventaire
        if inventory.inventory_type == 'dynamic':
            inventory_content = inventory.generate_inventory_content()
        else:
            inventory_content = inventory.content
        
        # Exécuter le playbook
        result = executor.execute_playbook(
            playbook_content=execution.playbook.content,
            inventory_content=inventory_content,
            extra_vars=execution.extra_vars,
            check_mode=execution.check_mode,
            limit=execution.limit,
            tags=execution.tags,
            skip_tags=execution.skip_tags,
            execution_id=str(execution.id)
        )
        
        # Mettre à jour l'exécution avec les résultats
        execution.output = result.get('stdout', '')
        execution.error_output = result.get('stderr', '')
        execution.return_code = result.get('return_code')
        execution.summary = result.get('summary', {})
        execution.host_results = result.get('host_results', {})
        execution.status = 'completed' if result.get('success') else 'failed'
        execution.completed_at = timezone.now()
        execution.save()
        
        logger.info(f"Execution {execution_id} completed with status: {execution.status}")
        
        # Mettre à jour les statistiques du playbook
        playbook = execution.playbook
        playbook.update_stats(
            success=execution.status == 'completed',
            duration=execution.duration or 0
        )
        
        # Envoyer des notifications si nécessaire
        if execution.status == 'failed':
            _send_failure_notification(execution)
        
        # Vérifier s'il y a des schedules à mettre à jour
        _update_schedules(execution)
        
        return {
            'execution_id': str(execution_id),
            'playbook': execution.playbook.name,
            'status': execution.status,
            'success': execution.status == 'completed',
            'duration': execution.duration,
            'summary': execution.summary
        }
        
    except PlaybookExecution.DoesNotExist:
        logger.error(f"Execution {execution_id} not found")
        return {'error': 'Execution not found'}
        
    except Exception as e:
        logger.exception(f"Execution failed: {str(e)}")
        
        # Mettre à jour l'exécution en cas d'erreur
        try:
            execution = PlaybookExecution.objects.get(id=execution_id)
            execution.status = 'failed'
            execution.error_output = str(e) + "\n" + traceback.format_exc()
            execution.completed_at = timezone.now()
            execution.save(update_fields=['status', 'error_output', 'completed_at'])
        except:
            pass
        
        # Réessayer la tâche
        self.retry(exc=e)


@shared_task
def process_scheduled_playbooks():
    """
    Tâche périodique pour traiter les playbooks planifiés
    Exécutée par Celery Beat
    """
    logger.info("Processing scheduled playbooks")
    
    now = timezone.now()
    
    # Récupérer les schedules actifs dont la prochaine exécution est <= maintenant
    schedules = PlaybookSchedule.objects.filter(
        status='active',
        next_run__lte=now,
        start_date__lte=now
    ).filter(
        Q(end_date__isnull=True) | Q(end_date__gte=now)
    ).select_related('playbook', 'inventory', 'created_by')
    
    executed_count = 0
    errors = []
    
    for schedule in schedules:
        try:
            logger.info(f"Processing schedule: {schedule.name}")
            
            # Vérifier que le playbook est actif
            if schedule.playbook.status != 'active':
                logger.warning(f"Schedule {schedule.id}: Playbook {schedule.playbook.name} is not active")
                schedule.status = 'failed'
                schedule.save(update_fields=['status'])
                continue
            
            # Créer une exécution
            execution = PlaybookExecution.objects.create(
                playbook=schedule.playbook,
                inventory=schedule.inventory,
                extra_vars=schedule.extra_vars,
                limit=schedule.limit,
                tags=schedule.tags,
                check_mode=schedule.check_mode,
                executed_by=schedule.created_by,
                status='pending'
            )
            
            # Prendre un snapshot de l'inventaire
            execution.take_inventory_snapshot()
            
            # Lancer l'exécution
            execute_playbook_task.delay(str(execution.id))
            
            # Mettre à jour la planification
            schedule.last_run = now
            schedule.execution_count += 1
            schedule.last_execution = execution
            
            # Calculer la prochaine exécution
            schedule.next_run = schedule.calculate_next_run()
            
            # Si schedule_type est 'once', marquer comme complété
            if schedule.schedule_type == 'once':
                schedule.status = 'completed'
            
            schedule.save()
            
            executed_count += 1
            logger.info(f"Schedule {schedule.id} executed, next run: {schedule.next_run}")
            
        except Exception as e:
            logger.exception(f"Error processing schedule {schedule.id}: {str(e)}")
            errors.append({'schedule': schedule.id, 'error': str(e)})
            
            # Marquer le schedule comme échoué si erreur grave
            schedule.status = 'failed'
            schedule.save(update_fields=['status'])
    
    logger.info(f"Scheduled playbooks processed: {executed_count} executed, {len(errors)} errors")
    
    return {
        'executed': executed_count,
        'errors': errors
    }


@shared_task
def cleanup_old_executions(days=30):
    """
    Nettoie les vieilles exécutions
    
    Args:
        days (int): Nombre de jours de conservation
    """
    from datetime import timedelta
    
    cutoff_date = timezone.now() - timedelta(days=days)
    
    # Supprimer les vieilles exécutions
    old_executions = PlaybookExecution.objects.filter(
        created_at__lt=cutoff_date,
        status__in=['completed', 'failed', 'cancelled', 'timeout']
    )
    
    count = old_executions.count()
    old_executions.delete()
    
    logger.info(f"Cleaned up {count} old executions")
    
    return {'deleted': count}


@shared_task
def sync_inventory_from_devices(inventory_id):
    """
    Synchronise un inventaire avec les devices associés
    
    Args:
        inventory_id (str): ID de l'inventaire
    """
    try:
        inventory = AnsibleInventory.objects.get(id=inventory_id)
        
        if inventory.inventory_type != 'static':
            inventory.content = inventory.generate_inventory_content()
            inventory.save(update_fields=['content'])
            
            logger.info(f"Inventory {inventory_id} synchronized")
            return {'success': True, 'inventory': inventory.name}
        
        return {'success': False, 'message': 'Static inventory not synced'}
        
    except AnsibleInventory.DoesNotExist:
        logger.error(f"Inventory {inventory_id} not found")
        return {'error': 'Inventory not found'}


@shared_task
def bulk_execute_playbooks(playbook_ids, extra_vars=None, user_id=None):
    """
    Exécute plusieurs playbooks en série
    
    Args:
        playbook_ids (list): Liste des IDs de playbooks
        extra_vars (dict): Variables supplémentaires
        user_id (int): ID de l'utilisateur
    """
    from apps.users.models import User
    
    user = User.objects.get(id=user_id) if user_id else None
    results = []
    
    for playbook_id in playbook_ids:
        try:
            # Créer une exécution pour chaque playbook
            from .models import Playbook
            playbook = Playbook.objects.get(id=playbook_id)
            
            execution = PlaybookExecution.objects.create(
                playbook=playbook,
                inventory=playbook.inventory,
                extra_vars=extra_vars or {},
                executed_by=user,
                status='pending'
            )
            
            # Lancer l'exécution
            execute_playbook_task.delay(str(execution.id))
            
            results.append({
                'playbook': playbook.name,
                'execution_id': str(execution.id),
                'status': 'queued'
            })
            
        except Exception as e:
            logger.error(f"Error queueing playbook {playbook_id}: {str(e)}")
            results.append({
                'playbook_id': str(playbook_id),
                'error': str(e)
            })
    
    return {'results': results}


def _send_failure_notification(execution):
    """Envoie une notification en cas d'échec"""
    try:
        # Vérifier s'il y a un schedule associé
        schedule = PlaybookSchedule.objects.filter(last_execution=execution).first()
        
        if schedule and schedule.notify_on_failure and schedule.notification_emails:
            subject = f"[Ansible] Échec d'exécution: {execution.playbook.name}"
            
            message = f"""
L'exécution du playbook a échoué:

Playbook: {execution.playbook.name}
Exécution ID: {execution.id}
Date: {execution.created_at}
Utilisateur: {execution.executed_by}

Code retour: {execution.return_code}

Résumé:
- Tasks OK: {execution.summary.get('ok', 0)}
- Tasks Changed: {execution.summary.get('changed', 0)}
- Tasks Failed: {execution.summary.get('failed', 0)}
- Unreachable: {execution.summary.get('unreachable', 0)}

Planification: {schedule.name}

Voir les détails dans l'interface d'administration.
            """
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                schedule.notification_emails,
                fail_silently=True,
            )
            
            logger.info(f"Failure notification sent for execution {execution.id}")
            
    except Exception as e:
        logger.error(f"Error sending notification: {str(e)}")


def _update_schedules(execution):
    """Met à jour les schedules liés à l'exécution"""
    try:
        # Vérifier si cette exécution est la dernière d'un schedule
        schedule = PlaybookSchedule.objects.filter(last_execution=execution).first()
        
        if schedule and schedule.notify_on_success and execution.status == 'completed':
            if schedule.notification_emails:
                subject = f"[Ansible] Exécution réussie: {execution.playbook.name}"
                
                message = f"""
L'exécution du playbook a réussi:

Playbook: {execution.playbook.name}
Exécution ID: {execution.id}
Date: {execution.created_at}
Durée: {execution.duration:.1f}s

Résumé:
- Tasks OK: {execution.summary.get('ok', 0)}
- Tasks Changed: {execution.summary.get('changed', 0)}

Planification: {schedule.name}
                """
                
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    schedule.notification_emails,
                    fail_silently=True,
                )
                
    except Exception as e:
        logger.error(f"Error updating schedules: {str(e)}")