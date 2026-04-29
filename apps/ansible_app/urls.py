# apps/ansible_app/urls.py
"""
Ansible App URLs - Configuration des routes API
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *

router = DefaultRouter()
router.register(r'inventories', AnsibleInventoryViewSet, basename='ansible-inventory')
router.register(r'playbooks', PlaybookViewSet, basename='playbook')
router.register(r'executions', PlaybookExecutionViewSet, basename='playbook-execution')
router.register(r'schedules', PlaybookScheduleViewSet, basename='playbook-schedule')
router.register(r'roles', AnsibleRoleViewSet, basename='ansible-role')
router.register(r'collections', AnsibleCollectionViewSet, basename='ansible-collection')
router.register(r'tasks', AnsibleTaskViewSet, basename='ansible-task')
router.register(r'vars', AnsibleVarsViewSet, basename='ansible-vars')
router.register(r'credentials', AnsibleCredentialViewSet, basename='ansible-credential')
router.register(r'dashboard', AnsibleDashboardViewSet, basename='ansible-dashboard')

urlpatterns = [
    path('', include(router.urls)),
]