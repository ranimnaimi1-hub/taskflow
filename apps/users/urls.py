from rest_framework.routers import DefaultRouter
from .views import UserViewSet, TeamViewSet, RoleViewSet, PermissionViewSet, UserActivityViewSet

router = DefaultRouter()
router.register('users', UserViewSet)
router.register('teams', TeamViewSet)
router.register('roles', RoleViewSet)
router.register('permissions', PermissionViewSet)
router.register('activities', UserActivityViewSet)

urlpatterns = router.urls
