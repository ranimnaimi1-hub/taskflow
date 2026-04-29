"""
Grafana App URLs - Configuration des routes API
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *

router = DefaultRouter()
router.register(r'servers', GrafanaServerViewSet, basename='grafana-server')
router.register(r'dashboards', GrafanaDashboardViewSet, basename='grafana-dashboard')
router.register(r'datasources', GrafanaDatasourceViewSet, basename='grafana-datasource')
router.register(r'alerts', GrafanaAlertViewSet, basename='grafana-alert')
router.register(r'organizations', GrafanaOrganizationViewSet, basename='grafana-organization')
router.register(r'users', GrafanaUserViewSet, basename='grafana-user')
router.register(r'folders', GrafanaFolderViewSet, basename='grafana-folder')
router.register(r'panels', GrafanaPanelViewSet, basename='grafana-panel')
router.register(r'snapshots', GrafanaSnapshotViewSet, basename='grafana-snapshot')
router.register(r'teams', GrafanaTeamViewSet, basename='grafana-team')
router.register(r'dashboard', GrafanaDashboardViewSet, basename='grafana-dashboard-summary')

urlpatterns = [
    path('', include(router.urls)),
]