"""
Jenkins App URLs - Configuration des routes API
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *

router = DefaultRouter()
router.register(r'servers', JenkinsServerViewSet, basename='jenkins-server')
router.register(r'jobs', JenkinsJobViewSet, basename='jenkins-job')
router.register(r'builds', JenkinsBuildViewSet, basename='jenkins-build')
router.register(r'nodes', JenkinsNodeViewSet, basename='jenkins-node')
router.register(r'plugins', JenkinsPluginViewSet, basename='jenkins-plugin')
router.register(r'credentials', JenkinsCredentialViewSet, basename='jenkins-credential')
router.register(r'views', JenkinsViewViewSet, basename='jenkins-view')
router.register(r'pipelines', JenkinsPipelineViewSet, basename='jenkins-pipeline')
router.register(r'dashboard', JenkinsDashboardViewSet, basename='jenkins-dashboard')

urlpatterns = [
    path('', include(router.urls)),
]