"""
Jenkins App Views - API endpoints professionnels
Version complète avec toutes les actions JenkinsClient
"""
from rest_framework import viewsets, status
from rest_framework import filters as drf_filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count, Q, Avg
from django.utils import timezone
from datetime import timedelta
import logging

from apps.core.permissions import IsActiveUser, HasAPIAccess
from apps.core.pagination import StandardPagination
from apps.core.responses import success_response, created_response, error_response

from .models import (
    JenkinsServer, JenkinsJob, JenkinsBuild, JenkinsNode,
    JenkinsPlugin, JenkinsCredential, JenkinsView, JenkinsPipeline
)
from .serializers import (
    JenkinsServerSerializer, JenkinsServerDetailSerializer,
    JenkinsJobSerializer, JenkinsJobDetailSerializer,
    JenkinsBuildSerializer, JenkinsBuildDetailSerializer,
    JenkinsNodeSerializer,
    JenkinsPluginSerializer,
    JenkinsCredentialSerializer,
    JenkinsViewSerializer,
    JenkinsPipelineSerializer, JenkinsPipelineDetailSerializer,
    JenkinsBuildTriggerSerializer, JenkinsJobSyncSerializer
)

from .filters import (
    JenkinsServerFilter,
    JenkinsJobFilter,
    JenkinsBuildFilter,
    JenkinsNodeFilter,
    JenkinsPluginFilter,
    JenkinsCredentialFilter,
    JenkinsViewFilter,
    JenkinsPipelineFilter
)

from .jenkins_client import JenkinsClient

logger = logging.getLogger(__name__)


# ============================================================================
# SERVEURS JENKINS
# ============================================================================

class JenkinsServerViewSet(viewsets.ModelViewSet):
    """ViewSet pour les serveurs Jenkins"""
    
    queryset = JenkinsServer.objects.select_related('created_by').prefetch_related(
        'jobs', 'nodes', 'plugins', 'views'
    ).all()
    
    serializer_class = JenkinsServerSerializer
    serializer_classes = {
        'retrieve': JenkinsServerDetailSerializer,
        'default': JenkinsServerSerializer
    }
    
    permission_classes = [IsAuthenticated, IsActiveUser, HasAPIAccess]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_class = JenkinsServerFilter
    search_fields = ['name', 'description', 'url']
    ordering_fields = ['name', 'created_at', 'last_sync_at']
    ordering = ['name']
    
    def get_serializer_class(self):
        return self.serializer_classes.get(self.action, self.serializer_classes['default'])
    
    def get_queryset(self):
        user = self.request.user
        
        if not user or not user.is_authenticated:
            return JenkinsServer.objects.none()
        
        if hasattr(user, 'role') and user.role in ['superadmin', 'admin']:
            return JenkinsServer.objects.all()
        
        return JenkinsServer.objects.filter(created_by=user)
    
    def perform_create(self, serializer):
        if self.request.user.is_authenticated:
            serializer.save(created_by=self.request.user)
        else:
            serializer.save()
    
    @action(detail=True, methods=['post'])
    def sync(self, request, pk=None):
        """Synchronise toutes les données du serveur Jenkins"""
        server = self.get_object()
        
        if not self._can_access_object(server):
            self.permission_denied(request)
        
        client = server.get_client()
        
        # Vérifier la connexion
        version_result = client.get_version()
        if not version_result['success']:
            return error_response("Cannot connect to Jenkins server", version_result)
        
        server.version = version_result.get('version', '')
        server.last_sync_at = timezone.now()
        server.save()
        
        # Synchroniser les jobs
        jobs_result = client.get_jobs()
        if jobs_result['success']:
            self._sync_jobs(server, jobs_result.get('jobs', []))
        
        # Synchroniser les nœuds
        self._sync_nodes(server, client)
        
        # Synchroniser les plugins
        self._sync_plugins(server, client)
        
        # Synchroniser les vues
        self._sync_views(server, client)
        
        return success_response(
            JenkinsServerDetailSerializer(server).data,
            "Server synchronized successfully"
        )
    
    @action(detail=True, methods=['get'])
    def test_connection(self, request, pk=None):
        """Teste la connexion au serveur Jenkins"""
        server = self.get_object()
        
        if not self._can_access_object(server):
            self.permission_denied(request)
        
        client = server.get_client()
        result = client.get_version()
        
        if result['success']:
            server.version = result.get('version', '')
            server.last_sync_at = timezone.now()
            server.save()
            
            return success_response(
                {'version': server.version},
                "Connection successful"
            )
        
        return error_response("Connection failed", result)
    
    @action(detail=True, methods=['get'])
    def jobs(self, request, pk=None):
        """Liste tous les jobs du serveur"""
        server = self.get_object()
        
        if not self._can_access_object(server):
            self.permission_denied(request)
        
        jobs = server.jobs.all()
        page = self.paginate_queryset(jobs)
        
        if page is not None:
            serializer = JenkinsJobSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = JenkinsJobSerializer(jobs, many=True)
        return success_response(serializer.data, "Jobs retrieved")
    
    @action(detail=True, methods=['get'])
    def builds(self, request, pk=None):
        """Liste tous les builds du serveur"""
        server = self.get_object()
        
        if not self._can_access_object(server):
            self.permission_denied(request)
        
        builds = JenkinsBuild.objects.filter(job__server=server)
        page = self.paginate_queryset(builds)
        
        if page is not None:
            serializer = JenkinsBuildSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = JenkinsBuildSerializer(builds, many=True)
        return success_response(serializer.data, "Builds retrieved")
    
    @action(detail=True, methods=['get'])
    def queue(self, request, pk=None):
        """Récupère la file d'attente des builds"""
        server = self.get_object()
        
        if not self._can_access_object(server):
            self.permission_denied(request)
        
        client = server.get_client()
        result = client.get_queue()
        
        if result['success']:
            return success_response(
                {'queue': result.get('queue', [])},
                "Queue retrieved"
            )
        
        return error_response("Failed to get queue", result)
    
    def _sync_jobs(self, server, jobs_data):
        """Synchronise les jobs avec les données Jenkins"""
        for job_data in jobs_data:
            job, created = JenkinsJob.objects.update_or_create(
                server=server,
                job_id=job_data.get('name'),
                defaults={
                    'name': job_data.get('name'),
                    'url': job_data.get('url'),
                    'color': job_data.get('color'),
                    'synced_at': timezone.now(),
                }
            )
            
            # Récupérer les détails du job
            client = server.get_client()
            job_info = client.get_job_info(job.job_id)
            if job_info['success']:
                self._update_job_details(job, job_info['job'])
    
    def _update_job_details(self, job, job_data):
        """Met à jour les détails d'un job"""
        job.description = job_data.get('description', '')
        job.job_type = 'pipeline' if 'pipeline' in str(job_data) else 'freestyle'
        
        # Dernier build
        last_build = job_data.get('lastBuild')
        if last_build:
            job.last_build_number = last_build.get('number', 0)
            job.last_build_status = last_build.get('result', '')
            job.last_build_at = timezone.datetime.fromtimestamp(
                last_build.get('timestamp', 0) / 1000
            ) if last_build.get('timestamp') else None
        
        job.save()
    
    def _sync_nodes(self, server, client):
        """Synchronise les nœuds Jenkins"""
        try:
            response = client.session.get(f'{client.url}/computer/api/json')
            if response.status_code == 200:
                data = response.json()
                computers = data.get('computer', [])
                
                for computer in computers:
                    node_name = computer.get('displayName', computer.get('name', 'master'))
                    node, created = JenkinsNode.objects.update_or_create(
                        server=server,
                        node_id=computer.get('name', 'master'),
                        defaults={
                            'name': node_name,
                            'node_type': 'master' if computer.get('name') == 'master' else 'agent',
                            'status': 'online' if not computer.get('offline') else 'offline',
                            'offline_reason': computer.get('offlineCauseReason', ''),
                            'num_executors': computer.get('numExecutors', 0),
                            'labels': [label.get('name') for label in computer.get('assignedLabels', [])],
                            'synced_at': timezone.now()
                        }
                    )
        except Exception as e:
            logger.error(f"Error syncing nodes: {str(e)}")
    
    def _sync_plugins(self, server, client):
        """Synchronise les plugins Jenkins"""
        try:
            response = client.session.get(f'{client.url}/pluginManager/api/json?depth=2')
            if response.status_code == 200:
                data = response.json()
                plugins = data.get('plugins', [])
                
                for plugin_data in plugins:
                    plugin, created = JenkinsPlugin.objects.update_or_create(
                        server=server,
                        plugin_id=plugin_data.get('shortName'),
                        defaults={
                            'name': plugin_data.get('shortName'),
                            'version': plugin_data.get('version'),
                            'title': plugin_data.get('longName', ''),
                            'description': plugin_data.get('description', ''),
                            'url': plugin_data.get('url', ''),
                            'enabled': plugin_data.get('enabled', True),
                            'has_update': plugin_data.get('hasUpdate', False),
                            'compatible_version': plugin_data.get('compatibleVersion', ''),
                            'dependencies': plugin_data.get('dependencies', []),
                            'installed_at': timezone.now(),
                            'updated_at': timezone.now()
                        }
                    )
        except Exception as e:
            logger.error(f"Error syncing plugins: {str(e)}")
    
    def _sync_views(self, server, client):
        """Synchronise les vues Jenkins"""
        try:
            response = client.session.get(f'{client.url}/api/json?tree=views[name,url,description]')
            if response.status_code == 200:
                data = response.json()
                views = data.get('views', [])
                
                for view_data in views:
                    view, created = JenkinsView.objects.update_or_create(
                        server=server,
                        view_id=view_data.get('name'),
                        defaults={
                            'name': view_data.get('name'),
                            'description': view_data.get('description', ''),
                            'url': view_data.get('url', ''),
                            'view_type': 'list',
                            'jobs': self._get_view_jobs(client, view_data.get('name')),
                            'synced_at': timezone.now()
                        }
                    )
        except Exception as e:
            logger.error(f"Error syncing views: {str(e)}")
    
    def _get_view_jobs(self, client, view_name):
        """Récupère les jobs d'une vue"""
        try:
            response = client.session.get(f'{client.url}/view/{view_name}/api/json?tree=jobs[name]')
            if response.status_code == 200:
                data = response.json()
                return [job.get('name') for job in data.get('jobs', [])]
        except:
            pass
        return []
    
    def _can_access_object(self, obj):
        user = self.request.user
        if not user or not user.is_authenticated:
            return False
        
        if hasattr(user, 'role') and user.role in ['superadmin', 'admin']:
            return True
        
        return obj.created_by == user


# ============================================================================
# JOBS JENKINS
# ============================================================================

class JenkinsJobViewSet(viewsets.ModelViewSet):
    """ViewSet pour les jobs Jenkins"""
    
    queryset = JenkinsJob.objects.select_related('server').prefetch_related('builds').all()
    serializer_class = JenkinsJobSerializer
    serializer_classes = {
        'retrieve': JenkinsJobDetailSerializer,
        'default': JenkinsJobSerializer
    }
    
    permission_classes = [IsAuthenticated, IsActiveUser, HasAPIAccess]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_class = JenkinsJobFilter
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'last_build_at', 'build_count']
    ordering = ['name']
    
    def get_serializer_class(self):
        return self.serializer_classes.get(self.action, self.serializer_classes['default'])
    
    def get_queryset(self):
        user = self.request.user
        
        if not user or not user.is_authenticated:
            return JenkinsJob.objects.none()
        
        if hasattr(user, 'role') and user.role in ['superadmin', 'admin']:
            return JenkinsJob.objects.all()
        
        return JenkinsJob.objects.filter(
            Q(server__created_by=user)
        ).distinct()
    
    @action(detail=True, methods=['post'])
    def build(self, request, pk=None):
        """Déclenche un build du job"""
        job = self.get_object()
        
        if not self._can_access_object(job):
            self.permission_denied(request)
        
        serializer = JenkinsBuildTriggerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        
        client = job.server.get_client()
        
        # Déclencher le build
        result = client.build_job(job.job_id, data.get('parameters'))
        
        if not result['success']:
            return error_response("Failed to trigger build", result)
        
        # Créer un enregistrement de build en attente
        build = JenkinsBuild.objects.create(
            job=job,
            build_number=job.last_build_number + 1,
            status='pending',
            parameters=data.get('parameters', {}),
            triggered_by=request.user if request.user.is_authenticated else None
        )
        
        # Mettre à jour le job
        job.last_build_number += 1
        job.last_build_at = timezone.now()
        job.save()
        
        return created_response(
            JenkinsBuildSerializer(build).data,
            "Build triggered successfully"
        )
    
    @action(detail=True, methods=['post'])
    def build_with_parameters(self, request, pk=None):
        """Déclenche un build avec des paramètres (alias)"""
        return self.build(request, pk)
    
    @action(detail=True, methods=['post'])
    def sync(self, request, pk=None):
        """Synchronise les détails du job depuis Jenkins"""
        job = self.get_object()
        
        if not self._can_access_object(job):
            self.permission_denied(request)
        
        serializer = JenkinsJobSyncSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        
        client = job.server.get_client()
        job_info = client.get_job_info(job.job_id)
        
        if not job_info['success']:
            return error_response("Failed to sync job", job_info)
        
        # Mettre à jour les détails du job
        job_data = job_info['job']
        job.description = job_data.get('description', '')
        job.url = job_data.get('url', '')
        job.synced_at = timezone.now()
        job.save()
        
        # Synchroniser les builds
        if data.get('sync_builds'):
            self._sync_builds(job, job_data, data.get('limit', 50))
        
        return success_response(
            JenkinsJobDetailSerializer(job).data,
            "Job synchronized successfully"
        )
    
    @action(detail=True, methods=['post'])
    def enable(self, request, pk=None):
        """Active le job"""
        job = self.get_object()
        
        if not self._can_access_object(job):
            self.permission_denied(request)
        
        client = job.server.get_client()
        response = client.session.post(f'{client.url}/job/{job.job_id}/enable')
        
        if response.status_code == 200:
            job.is_active = True
            job.save()
            return success_response(None, "Job enabled")
        
        return error_response("Failed to enable job")
    
    @action(detail=True, methods=['post'])
    def disable(self, request, pk=None):
        """Désactive le job"""
        job = self.get_object()
        
        if not self._can_access_object(job):
            self.permission_denied(request)
        
        client = job.server.get_client()
        response = client.session.post(f'{client.url}/job/{job.job_id}/disable')
        
        if response.status_code == 200:
            job.is_active = False
            job.save()
            return success_response(None, "Job disabled")
        
        return error_response("Failed to disable job")
    
    @action(detail=True, methods=['get'])
    def config(self, request, pk=None):
        """Récupère la configuration XML du job"""
        job = self.get_object()
        
        if not self._can_access_object(job):
            self.permission_denied(request)
        
        client = job.server.get_client()
        response = client.session.get(f'{client.url}/job/{job.job_id}/config.xml')
        
        if response.status_code == 200:
            return success_response(
                {'config_xml': response.text},
                "Job configuration retrieved"
            )
        
        return error_response("Failed to get job configuration")
    
    @action(detail=True, methods=['post'])
    def update_config(self, request, pk=None):
        """Met à jour la configuration XML du job"""
        job = self.get_object()
        
        if not self._can_access_object(job):
            self.permission_denied(request)
        
        config_xml = request.data.get('config_xml')
        if not config_xml:
            return error_response("config_xml is required")
        
        client = job.server.get_client()
        headers = {'Content-Type': 'application/xml'}
        response = client.session.post(
            f'{client.url}/job/{job.job_id}/config.xml',
            data=config_xml,
            headers=headers
        )
        
        if response.status_code == 200:
            job.config_xml = config_xml
            job.save()
            return success_response(None, "Job configuration updated")
        
        return error_response("Failed to update job configuration")
    
    def _sync_builds(self, job, job_data, limit=50):
        """Synchronise l'historique des builds"""
        builds_data = job_data.get('builds', [])[:limit]
        client = job.server.get_client()
        
        for build_data in builds_data:
            build_number = build_data.get('number')
            
            # Récupérer les détails du build
            build_info = client.get_build_info(job.job_id, build_number)
            if not build_info['success']:
                continue
            
            build_details = build_info['build']
            
            # Récupérer la console
            console = client.get_build_console(job.job_id, build_number)
            
            # Récupérer les résultats des tests
            test_results = {}
            try:
                test_response = client.session.get(
                    f'{client.url}/job/{job.job_id}/{build_number}/testReport/api/json'
                )
                if test_response.status_code == 200:
                    test_results = test_response.json()
            except:
                pass
            
            # Créer ou mettre à jour le build
            build, created = JenkinsBuild.objects.update_or_create(
                job=job,
                build_number=build_number,
                defaults={
                    'status': self._map_build_status(build_details.get('result')),
                    'result': build_details.get('result', ''),
                    'url': build_details.get('url', ''),
                    'started_at': timezone.datetime.fromtimestamp(
                        build_details.get('timestamp', 0) / 1000
                    ) if build_details.get('timestamp') else None,
                    'duration': build_details.get('duration', 0) / 1000 if build_details.get('duration') else None,
                    'estimated_duration': build_details.get('estimatedDuration', 0) / 1000 if build_details.get('estimatedDuration') else None,
                    'built_by': build_details.get('builtBy', ''),
                    'console_output': console.get('console', '') if console.get('success') else '',
                    'test_results': test_results,
                }
            )
    
    def _map_build_status(self, result):
        """Convertit le résultat Jenkins en statut interne"""
        if not result:
            return 'pending'
        if result == 'SUCCESS':
            return 'completed'
        if result == 'FAILURE':
            return 'failed'
        if result == 'UNSTABLE':
            return 'unstable'
        if result == 'ABORTED':
            return 'aborted'
        return 'pending'
    
    def _can_access_object(self, obj):
        user = self.request.user
        if not user or not user.is_authenticated:
            return False
        
        if hasattr(user, 'role') and user.role in ['superadmin', 'admin']:
            return True
        
        return obj.server.created_by == user


# ============================================================================
# BUILDS JENKINS
# ============================================================================

class JenkinsBuildViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet pour les builds Jenkins (lecture seule)"""
    
    queryset = JenkinsBuild.objects.select_related('job', 'job__server', 'triggered_by').all()
    serializer_class = JenkinsBuildSerializer
    serializer_classes = {
        'retrieve': JenkinsBuildDetailSerializer,
        'default': JenkinsBuildSerializer
    }
    
    permission_classes = [IsAuthenticated, IsActiveUser, HasAPIAccess]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_class = JenkinsBuildFilter
    search_fields = ['job__name']
    ordering_fields = ['build_number', 'started_at', 'duration']
    ordering = ['-build_number']
    
    def get_serializer_class(self):
        return self.serializer_classes.get(self.action, self.serializer_classes['default'])
    
    def get_queryset(self):
        user = self.request.user
        
        if not user or not user.is_authenticated:
            return JenkinsBuild.objects.none()
        
        if hasattr(user, 'role') and user.role in ['superadmin', 'admin']:
            return JenkinsBuild.objects.all()
        
        return JenkinsBuild.objects.filter(
            Q(job__server__created_by=user)
        ).distinct()
    
    @action(detail=True, methods=['get'])
    def console(self, request, pk=None):
        """Récupère la console output du build"""
        build = self.get_object()
        
        if not self._can_view_object(build):
            self.permission_denied(request)
        
        # Si la console est déjà en base, la retourner
        if build.console_output:
            return success_response(
                {'console': build.console_output},
                "Console output retrieved"
            )
        
        # Sinon, la récupérer depuis Jenkins
        client = build.job.server.get_client()
        result = client.get_build_console(build.job.job_id, build.build_number)
        
        if result['success']:
            build.console_output = result.get('console', '')
            build.save(update_fields=['console_output'])
            return success_response(
                {'console': build.console_output},
                "Console output retrieved"
            )
        
        return error_response("Failed to get console output", result)
    
    @action(detail=True, methods=['post'])
    def stop(self, request, pk=None):
        """Arrête un build en cours"""
        build = self.get_object()
        
        if not self._can_view_object(build):
            self.permission_denied(request)
        
        if build.status != 'running':
            return error_response("Build is not running")
        
        client = build.job.server.get_client()
        result = client.stop_build(build.job.job_id, build.build_number)
        
        if result['success']:
            build.status = 'aborted'
            build.completed_at = timezone.now()
            build.save()
            return success_response(None, "Build stopped")
        
        return error_response("Failed to stop build", result)
    
    @action(detail=True, methods=['get'])
    def tests(self, request, pk=None):
        """Récupère les résultats des tests"""
        build = self.get_object()
        
        if not self._can_view_object(build):
            self.permission_denied(request)
        
        if build.test_results:
            return success_response(
                build.test_results,
                "Test results retrieved"
            )
        
        # Récupérer les résultats des tests depuis Jenkins
        client = build.job.server.get_client()
        response = client.session.get(
            f'{client.url}/job/{build.job.job_id}/{build.build_number}/testReport/api/json'
        )
        
        if response.status_code == 200:
            test_results = response.json()
            build.test_results = test_results
            build.save(update_fields=['test_results'])
            return success_response(test_results, "Test results retrieved")
        
        return success_response({}, "No test results found")
    
    @action(detail=True, methods=['get'])
    def artifacts(self, request, pk=None):
        """Liste les artifacts du build"""
        build = self.get_object()
        
        if not self._can_view_object(build):
            self.permission_denied(request)
        
        if build.artifacts:
            return success_response(
                build.artifacts,
                "Artifacts retrieved"
            )
        
        # Récupérer les artifacts depuis Jenkins
        client = build.job.server.get_client()
        response = client.session.get(
            f'{client.url}/job/{build.job.job_id}/{build.build_number}/api/json?tree=artifacts[*]'
        )
        
        if response.status_code == 200:
            data = response.json()
            artifacts = data.get('artifacts', [])
            build.artifacts = artifacts
            build.save(update_fields=['artifacts'])
            return success_response(artifacts, "Artifacts retrieved")
        
        return success_response([], "No artifacts found")
    
    def _can_view_object(self, obj):
        user = self.request.user
        if not user or not user.is_authenticated:
            return False
        
        if hasattr(user, 'role') and user.role in ['superadmin', 'admin']:
            return True
        
        return obj.job.server.created_by == user


# ============================================================================
# NŒUDS JENKINS
# ============================================================================

class JenkinsNodeViewSet(viewsets.ModelViewSet):
    """ViewSet pour les nœuds Jenkins"""
    
    queryset = JenkinsNode.objects.select_related('server').all()
    serializer_class = JenkinsNodeSerializer
    permission_classes = [IsAuthenticated, IsActiveUser, HasAPIAccess]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_class = JenkinsNodeFilter
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'status']
    ordering = ['name']
    
    def get_queryset(self):
        user = self.request.user
        
        if not user or not user.is_authenticated:
            return JenkinsNode.objects.none()
        
        if hasattr(user, 'role') and user.role in ['superadmin', 'admin']:
            return JenkinsNode.objects.all()
        
        return JenkinsNode.objects.filter(server__created_by=user)
    
    @action(detail=True, methods=['post'])
    def toggle_offline(self, request, pk=None):
        """Met le nœud en ligne/hors ligne"""
        node = self.get_object()
        
        if not self._can_access_object(node):
            self.permission_denied(request)
        
        client = node.server.get_client()
        message = request.data.get('message', 'Toggled by API')
        
        if node.status == 'online':
            # Mettre hors ligne
            url = f'{client.url}/computer/{node.node_id}/doToggleOffline?offlineMessage={message}'
        else:
            # Remettre en ligne
            url = f'{client.url}/computer/{node.node_id}/toggleOffline'
        
        response = client.session.post(url)
        
        if response.status_code == 200:
            node.status = 'offline' if node.status == 'online' else 'online'
            node.save()
            return success_response(
                {'status': node.status},
                f"Node {node.status}"
            )
        
        return error_response("Failed to toggle node status")
    
    def _can_access_object(self, obj):
        user = self.request.user
        if not user or not user.is_authenticated:
            return False
        
        if hasattr(user, 'role') and user.role in ['superadmin', 'admin']:
            return True
        
        return obj.server.created_by == user


# ============================================================================
# PLUGINS JENKINS
# ============================================================================

class JenkinsPluginViewSet(viewsets.ModelViewSet):
    """ViewSet pour les plugins Jenkins"""
    
    queryset = JenkinsPlugin.objects.select_related('server').all()
    serializer_class = JenkinsPluginSerializer
    permission_classes = [IsAuthenticated, IsActiveUser, HasAPIAccess]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_class = JenkinsPluginFilter
    search_fields = ['name', 'title', 'description']
    ordering_fields = ['name', 'version']
    ordering = ['name']
    
    def get_queryset(self):
        user = self.request.user
        
        if not user or not user.is_authenticated:
            return JenkinsPlugin.objects.none()
        
        if hasattr(user, 'role') and user.role in ['superadmin', 'admin']:
            return JenkinsPlugin.objects.all()
        
        return JenkinsPlugin.objects.filter(server__created_by=user)


# ============================================================================
# CREDENTIALS JENKINS
# ============================================================================

class JenkinsCredentialViewSet(viewsets.ModelViewSet):
    """ViewSet pour les credentials Jenkins"""
    
    queryset = JenkinsCredential.objects.select_related('server').all()
    serializer_class = JenkinsCredentialSerializer
    permission_classes = [IsAuthenticated, IsActiveUser, HasAPIAccess]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_class = JenkinsCredentialFilter
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    def get_queryset(self):
        user = self.request.user
        
        if not user or not user.is_authenticated:
            return JenkinsCredential.objects.none()
        
        if hasattr(user, 'role') and user.role in ['superadmin', 'admin']:
            return JenkinsCredential.objects.all()
        
        return JenkinsCredential.objects.filter(server__created_by=user)
    
    def perform_create(self, serializer):
        if self.request.user.is_authenticated:
            serializer.save()
        else:
            serializer.save()


# ============================================================================
# VUES JENKINS
# ============================================================================

class JenkinsViewViewSet(viewsets.ModelViewSet):
    """ViewSet pour les vues Jenkins"""
    
    queryset = JenkinsView.objects.select_related('server').all()
    serializer_class = JenkinsViewSerializer
    permission_classes = [IsAuthenticated, IsActiveUser, HasAPIAccess]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_class = JenkinsViewFilter
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    def get_queryset(self):
        user = self.request.user
        
        if not user or not user.is_authenticated:
            return JenkinsView.objects.none()
        
        if hasattr(user, 'role') and user.role in ['superadmin', 'admin']:
            return JenkinsView.objects.all()
        
        return JenkinsView.objects.filter(server__created_by=user)


# ============================================================================
# PIPELINES JENKINS
# ============================================================================

class JenkinsPipelineViewSet(viewsets.ModelViewSet):
    """ViewSet pour les pipelines Jenkins"""
    
    queryset = JenkinsPipeline.objects.prefetch_related('jobs', 'created_by').all()
    serializer_class = JenkinsPipelineSerializer
    serializer_classes = {
        'retrieve': JenkinsPipelineDetailSerializer,
        'default': JenkinsPipelineSerializer
    }
    
    permission_classes = [IsAuthenticated, IsActiveUser, HasAPIAccess]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_class = JenkinsPipelineFilter
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    def get_serializer_class(self):
        return self.serializer_classes.get(self.action, self.serializer_classes['default'])
    
    def get_queryset(self):
        user = self.request.user
        
        if not user or not user.is_authenticated:
            return JenkinsPipeline.objects.none()
        
        if hasattr(user, 'role') and user.role in ['superadmin', 'admin']:
            return JenkinsPipeline.objects.all()
        
        return JenkinsPipeline.objects.filter(created_by=user)
    
    def perform_create(self, serializer):
        if self.request.user.is_authenticated:
            serializer.save(created_by=self.request.user)
        else:
            serializer.save()
    
    @action(detail=True, methods=['post'])
    def run(self, request, pk=None):
        """Exécute la pipeline sur tous ses jobs"""
        pipeline = self.get_object()
        
        if not self._can_access_object(pipeline):
            self.permission_denied(request)
        
        results = []
        for job in pipeline.jobs.all():
            client = job.server.get_client()
            result = client.build_job(job.job_id, pipeline.parameters)
            
            if result['success']:
                # Créer un build
                build = JenkinsBuild.objects.create(
                    job=job,
                    build_number=job.last_build_number + 1,
                    status='pending',
                    parameters=pipeline.parameters,
                    triggered_by=request.user if request.user.is_authenticated else None
                )
                
                job.last_build_number += 1
                job.last_build_at = timezone.now()
                job.save()
                
                results.append({
                    'job': job.name,
                    'success': True,
                    'build_id': str(build.id)
                })
            else:
                results.append({
                    'job': job.name,
                    'success': False,
                    'error': result.get('error')
                })
        
        return success_response(results, "Pipeline executed")
    
    def _can_access_object(self, obj):
        user = self.request.user
        if not user or not user.is_authenticated:
            return False
        
        if hasattr(user, 'role') and user.role in ['superadmin', 'admin']:
            return True
        
        return obj.created_by == user


# ============================================================================
# DASHBOARD JENKINS
# ============================================================================

# ============================================================================
# DASHBOARD JENKINS
# ============================================================================

class JenkinsDashboardViewSet(viewsets.ViewSet):
    """Dashboard pour Jenkins"""
    permission_classes = [IsAuthenticated, IsActiveUser, HasAPIAccess]
    
    def _get_user_querysets(self, user):
        is_admin = hasattr(user, 'role') and user.role in ['superadmin', 'admin']
        
        if is_admin:
            servers = JenkinsServer.objects.all()
            jobs = JenkinsJob.objects.all()
            builds = JenkinsBuild.objects.all()
        else:
            servers = JenkinsServer.objects.filter(created_by=user)
            jobs = JenkinsJob.objects.filter(server__created_by=user)
            builds = JenkinsBuild.objects.filter(job__server__created_by=user)
        
        return servers, jobs, builds, is_admin  # ← Retourner is_admin aussi
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Résumé des activités Jenkins"""
        user = request.user
        
        if not user or not user.is_authenticated:
            return error_response("Authentication required")
        
        # Récupérer is_admin avec les autres valeurs
        servers, jobs, builds, is_admin = self._get_user_querysets(user)
        
        last_24h = timezone.now() - timedelta(hours=24)
        recent_builds = builds.filter(created_at__gte=last_24h)
        
        successful = recent_builds.filter(status='completed').count()
        failed = recent_builds.filter(status='failed').count()
        total = recent_builds.count()
        success_rate = (successful / total * 100) if total > 0 else 0
        
        # Récupérer la file d'attente du premier serveur actif
        queue_size = 0
        idle_executors = 0
        active_server = servers.filter(status='active').first()
        if active_server:
            client = active_server.get_client()
            queue_result = client.get_queue()
            if queue_result['success']:
                queue_size = len(queue_result.get('queue', []))
        
        data = {
            'statistics': {
                'total_servers': servers.count(),
                'active_servers': servers.filter(status='active').count(),
                'total_jobs': jobs.count(),
                'total_pipelines': JenkinsPipeline.objects.filter(
                    created_by=user if not is_admin else None
                ).count(),
                'builds_24h': total,
                'successful_builds_24h': successful,
                'failed_builds_24h': failed,
                'success_rate_24h': round(success_rate, 2),
                'avg_duration_24h': round(recent_builds.aggregate(avg=Avg('duration'))['avg'] or 0, 2),
                'queue_size': queue_size,
                'idle_executors': idle_executors,
            },
            'recent_builds': [
                {
                    'id': str(b.id),
                    'job_name': b.job.name,
                    'build_number': b.build_number,
                    'status': b.status,
                    'result': b.result,
                    'started_at': b.started_at,
                    'duration': b.duration,
                    'built_by': b.built_by
                }
                for b in builds.order_by('-created_at')[:10]
            ],
            'top_jobs': [
                {
                    'id': str(j.id),
                    'name': j.name,
                    'build_count': j.build_count,
                    'last_build_status': j.last_build_status,
                    'success_rate': self._calculate_success_rate(j)
                }
                for j in jobs.annotate(build_count=Count('builds')).order_by('-build_count')[:5]
            ],
            'queue': [],
            'nodes_status': {
                'online': JenkinsNode.objects.filter(server__in=servers, status='online').count(),
                'offline': JenkinsNode.objects.filter(server__in=servers, status='offline').count(),
                'total': JenkinsNode.objects.filter(server__in=servers).count()
            }
        }
        
        return success_response(data, "Dashboard summary retrieved")
    
    def _calculate_success_rate(self, job):
        """Calcule le taux de succès d'un job"""
        total = job.builds.count()
        if total == 0:
            return 0
        success = job.builds.filter(status='completed').count()
        return round((success / total) * 100, 2)