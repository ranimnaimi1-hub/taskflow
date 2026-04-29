# apps/terraform_app/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *

router = DefaultRouter()
router.register(r'configs', TerraformConfigViewSet, basename='terraform-config')
router.register(r'plans', TerraformPlanViewSet, basename='terraform-plan')
router.register(r'applies', TerraformApplyViewSet, basename='terraform-apply')
router.register(r'modules', TerraformModuleViewSet, basename='terraform-module')
router.register(r'providers', TerraformProviderViewSet, basename='terraform-provider')
router.register(r'variables', TerraformVariableViewSet, basename='terraform-variable')
router.register(r'credentials', TerraformCredentialViewSet, basename='terraform-credential')
router.register(r'dashboard', TerraformDashboardViewSet, basename='terraform-dashboard')

urlpatterns = [
    path('', include(router.urls)),
]