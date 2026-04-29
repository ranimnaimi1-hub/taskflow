"""
NetDevOps Platform URLs - Ultra Professional
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import permissions
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

# drf-yasg schema
schema_view_yasg = get_schema_view(
    openapi.Info(
        title="NetDevOps Platform API",
        default_version='v1',
        description="Ultra Professional Network DevOps Automation Platform",
        contact=openapi.Contact(email="admin@netdevops.com"),
        license=openapi.License(name="Proprietary"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    path('admin/', admin.site.urls),

    # ─────────────────────────────────────────────
    # PROMETHEUS METRICS (ADDED)
    # ─────────────────────────────────────────────
    path('', include('django_prometheus.urls')),

    # JWT Authentication
    path('api/auth/jwt/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/jwt/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/auth/jwt/verify/', TokenVerifyView.as_view(), name='token_verify'),

    # drf-spectacular (OpenAPI 3.0) - PREFERRED
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    # APPLICATIONS
    path('api/users/', include('apps.users.urls')),
    path('api/inventory/', include('apps.inventory.urls')),
    path('api/ansible/', include('apps.ansible_app.urls')),
    path('api/terraform/', include('apps.terraform_app.urls')),
    path('api/jenkins/', include('apps.jenkins_app.urls')),
    path('api/grafana/', include('apps.grafana_app.urls')),
    path('api/eveng/', include('apps.eveng_app.urls')),
    path('api/monitoring/', include('apps.monitoring.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    try:
        import debug_toolbar
        urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns
    except ImportError:
        pass