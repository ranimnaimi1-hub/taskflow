# debug_ansible.py
import os
import django
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

try:
    django.setup()
    print("✅ Django setup OK avec config.settings.development")
except Exception as e:
    print(f"❌ Erreur Django setup: {e}")
    sys.exit(1)

from django.test import RequestFactory
from rest_framework.test import force_authenticate, APIRequestFactory
from rest_framework.request import Request
from django.contrib.auth.models import AnonymousUser
from apps.users.models import User
from apps.ansible_app import views

def test_viewset(name, view_class):
    print(f"\n--- Test de {name} ---")
    
    # Utiliser APIRequestFactory au lieu de RequestFactory
    factory = APIRequestFactory()
    
    # Récupérer l'utilisateur
    try:
        user = User.objects.filter(email='msautoai3@gmail.com').first()
        if not user:
            print("⚠️  Superadmin non trouvé")
            return
        print(f"✅ Utilisateur: {user.email} (rôle: {user.role})")
    except Exception as e:
        print(f"❌ Erreur utilisateur: {e}")
        return
    
    # Créer une requête et y attacher l'utilisateur
    request = factory.get(f'/api/ansible/{name}/')
    
    # IMPORTANT: Ajouter l'utilisateur à la requête
    request.user = user
    
    # Créer une instance DRF Request
    drf_request = Request(request)
    
    # Instancier la vue
    try:
        view = view_class()
        view.request = drf_request
        view.action = 'list'
        view.format_kwarg = {}
        view.args = []
        view.kwargs = {}
        
        print(f"  ✅ Instanciation et configuration OK")
    except Exception as e:
        print(f"  ❌ Instanciation: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Test de get_queryset
    try:
        queryset = view.get_queryset()
        print(f"  ✅ get_queryset() retourne {queryset.count()} objets")
    except Exception as e:
        print(f"  ❌ get_queryset(): {e}")
        import traceback
        traceback.print_exc()
    
    # Test de get_serializer_class (seulement si la méthode existe)
    try:
        if hasattr(view, 'get_serializer_class'):
            serializer_class = view.get_serializer_class()
            print(f"  ✅ get_serializer_class() -> {serializer_class.__name__}")
        else:
            print(f"  ⚠️  Pas de méthode get_serializer_class (normal pour {name})")
    except Exception as e:
        print(f"  ❌ get_serializer_class(): {e}")
    
    # Test de la sérialisation (seulement si la méthode existe)
    try:
        if hasattr(view, 'get_queryset') and hasattr(view, 'get_serializer'):
            queryset = view.get_queryset()
            if queryset.exists():
                obj = queryset.first()
                serializer = view.get_serializer(obj)
                data = serializer.data
                print(f"  ✅ Sérialisation OK - {len(data)} champs")
            else:
                print(f"  ⚠️  Aucun objet à sérialiser dans {name}")
    except Exception as e:
        print(f"  ❌ Sérialisation: {e}")

def main():
    print("="*60)
    print("TEST DE TOUS LES VIEWSETS ANSIBLE")
    print("="*60)
    print(f"Settings utilisé: {os.environ.get('DJANGO_SETTINGS_MODULE')}")
    print("="*60)
    
    views_to_test = [
        ('inventories', views.AnsibleInventoryViewSet),
        ('playbooks', views.PlaybookViewSet),
        ('executions', views.PlaybookExecutionViewSet),
        ('schedules', views.PlaybookScheduleViewSet),
        ('roles', views.AnsibleRoleViewSet),
        ('collections', views.AnsibleCollectionViewSet),
        ('tasks', views.AnsibleTaskViewSet),
        ('vars', views.AnsibleVarsViewSet),
        ('credentials', views.AnsibleCredentialViewSet),
        ('dashboard', views.AnsibleDashboardViewSet),
    ]
    
    for name, view_class in views_to_test:
        test_viewset(name, view_class)

if __name__ == '__main__':
    main()