"""
EVE-NG App URLs - Configuration des routes API
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *

router = DefaultRouter()
router.register(r'servers', EVENServerViewSet, basename='eveng-server')
router.register(r'labs', EVENLabViewSet, basename='eveng-lab')
router.register(r'nodes', EVENNodeViewSet, basename='eveng-node')
router.register(r'networks', EVENNetworkViewSet, basename='eveng-network')
router.register(r'links', EVENLinkViewSet, basename='eveng-link')
router.register(r'images', EVENImageViewSet, basename='eveng-image')
router.register(r'sessions', EVENUserSessionViewSet, basename='eveng-session')
router.register(r'dashboard', EVENDashboardViewSet, basename='eveng-dashboard')

urlpatterns = [
    path('', include(router.urls)),
]