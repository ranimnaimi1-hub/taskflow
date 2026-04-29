# config/celery.py
import os
from celery import Celery
from celery.schedules import crontab

# Définir les settings Django par défaut
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.base")

# Créer l'application Celery
app = Celery("netdevops")

# Charger la configuration depuis Django settings
app.config_from_object("django.conf:settings", namespace="CELERY")

# Configuration du beat schedule (planification des tâches)
app.conf.beat_schedule = {
    'process-scheduled-playbooks': {
        'task': 'apps.ansible_app.tasks.process_scheduled_playbooks',
        'schedule': crontab(minute='*'),  # Chaque minute
        'options': {
            'queue': 'default',
            'priority': 5,
        }
    },
    'cleanup-old-executions': {
        'task': 'apps.ansible_app.tasks.cleanup_old_executions',
        'schedule': crontab(hour=2, minute=0),  # Chaque jour à 2h
        'args': (30,),  # 30 jours
        'options': {
            'queue': 'default',
            'priority': 1,
        }
    },
    # Optionnel : synchronisation périodique des inventaires
    'sync-inventories-hourly': {
        'task': 'apps.ansible_app.tasks.sync_inventories_task',
        'schedule': crontab(minute='0'),  # Toutes les heures
        'options': {
            'queue': 'default',
            'priority': 3,
        }
    },
}

# Découvrir automatiquement les tâches dans les apps installées
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """
    Tâche de debug pour vérifier que Celery fonctionne
    """
    print(f"Request: {self.request!r}")
    print(f"Celery is working! Time: {self.request.timestamp}")
    return {"status": "ok", "message": "Celery debug task executed"}


# Tâche utilitaire pour tester les beats
@app.task(bind=True)
def test_beat_task(self):
    """
    Tâche de test pour vérifier que le beat scheduler fonctionne
    """
    print(f"Beat task executed at: {self.request.timestamp}")
    return {"status": "ok", "beat": "working"}