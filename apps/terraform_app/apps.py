from django.apps import AppConfig


class TerraformAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = 'apps.terraform_app'
    verbose_name = "Terraform"

