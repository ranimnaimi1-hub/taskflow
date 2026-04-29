"""
Monitoring App URLs - Configuration des routes API
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *

router = DefaultRouter()
router.register(r'system-metrics', SystemMetricViewSet, basename='system-metric')
router.register(r'device-metrics', DeviceMetricViewSet, basename='device-metric')
router.register(r'interface-metrics', InterfaceMetricViewSet, basename='interface-metric')
router.register(r'application-metrics', ApplicationMetricViewSet, basename='application-metric')
router.register(r'alerts', AlertViewSet, basename='alert')
router.register(r'thresholds', AlertThresholdViewSet, basename='alert-threshold')
router.register(r'notification-channels', NotificationChannelViewSet, basename='notification-channel')
router.register(r'notification-logs', NotificationLogViewSet, basename='notification-log')
router.register(r'dashboards', DashboardViewSet, basename='dashboard')
router.register(r'metric-collections', MetricCollectionViewSet, basename='metric-collection')
router.register(r'dashboard', MonitoringDashboardViewSet, basename='monitoring-dashboard')

urlpatterns = [
    path('', include(router.urls)),
]