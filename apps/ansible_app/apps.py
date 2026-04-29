from django.apps import AppConfig


class AnsibleAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = 'apps.ansible_app'
    verbose_name = "Ansible Automation"

