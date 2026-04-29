"""
Monitoring Collectors - Professional Implementation
Collect metrics from various sources
"""
import psutil
import time
from datetime import datetime
from django.utils import timezone


class SystemCollector:
    """Collect system metrics"""
    
    @staticmethod
    def collect_cpu():
        """Collect CPU metrics"""
        return {
            'usage_percent': psutil.cpu_percent(interval=1),
            'count': psutil.cpu_count(),
            'load_avg': psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None,
            'timestamp': timezone.now()
        }
    
    @staticmethod
    def collect_memory():
        """Collect memory metrics"""
        mem = psutil.virtual_memory()
        return {
            'total': mem.total,
            'available': mem.available,
            'used': mem.used,
            'percent': mem.percent,
            'timestamp': timezone.now()
        }
    
    @staticmethod
    def collect_disk():
        """Collect disk metrics"""
        disk = psutil.disk_usage('/')
        return {
            'total': disk.total,
            'used': disk.used,
            'free': disk.free,
            'percent': disk.percent,
            'timestamp': timezone.now()
        }
    
    @staticmethod
    def collect_network():
        """Collect network metrics"""
        net = psutil.net_io_counters()
        return {
            'bytes_sent': net.bytes_sent,
            'bytes_recv': net.bytes_recv,
            'packets_sent': net.packets_sent,
            'packets_recv': net.packets_recv,
            'timestamp': timezone.now()
        }
    
    @staticmethod
    def collect_all():
        """Collect all system metrics"""
        return {
            'cpu': SystemCollector.collect_cpu(),
            'memory': SystemCollector.collect_memory(),
            'disk': SystemCollector.collect_disk(),
            'network': SystemCollector.collect_network(),
            'timestamp': timezone.now()
        }


class DeviceCollector:
    """Collect metrics from network devices"""
    
    @staticmethod
    def collect_device_health(device):
        """Collect device health metrics"""
        return {
            'device_id': device.id,
            'hostname': device.hostname,
            'cpu_usage': device.cpu_usage,
            'memory_usage': device.memory_usage,
            'temperature': device.temperature,
            'uptime': device.uptime_seconds,
            'is_reachable': device.is_reachable,
            'timestamp': timezone.now()
        }
    
    @staticmethod
    def collect_interface_stats(interface):
        """Collect interface statistics"""
        return {
            'interface_id': interface.id,
            'device_id': interface.device.id,
            'name': interface.name,
            'status': interface.status,
            'rx_bytes': interface.rx_bytes,
            'tx_bytes': interface.tx_bytes,
            'rx_packets': interface.rx_packets,
            'tx_packets': interface.tx_packets,
            'rx_errors': interface.rx_errors,
            'tx_errors': interface.tx_errors,
            'timestamp': timezone.now()
        }


class ApplicationCollector:
    """Collect application metrics"""
    
    @staticmethod
    def collect_ansible_stats():
        """Collect Ansible execution statistics"""
        from apps.ansible_app.models import PlaybookExecution
        total = PlaybookExecution.objects.count()
        completed = PlaybookExecution.objects.filter(status='completed').count()
        failed = PlaybookExecution.objects.filter(status='failed').count()
        
        return {
            'total_executions': total,
            'completed': completed,
            'failed': failed,
            'success_rate': (completed / total * 100) if total > 0 else 0,
            'timestamp': timezone.now()
        }
    
    @staticmethod
    def collect_user_stats():
        """Collect user statistics"""
        from apps.users.models import User, UserActivity
        return {
            'total_users': User.objects.count(),
            'active_users': User.objects.filter(is_active=True).count(),
            'total_activities': UserActivity.objects.count(),
            'activities_today': UserActivity.objects.filter(
                created_at__date=timezone.now().date()
            ).count(),
            'timestamp': timezone.now()
        }