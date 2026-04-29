from django.apps import AppConfig


class JenkinsAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = 'apps.jenkins_app'
    verbose_name = "Jenkins"