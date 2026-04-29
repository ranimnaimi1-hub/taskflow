# apps/inventory/utils/ipam_utils.py
"""
IPAM Utilities - Gestionnaire d'adresses IP
"""
import ipaddress
from ..models import Prefix, IPAddress, VRF


class IPAMManager:
    """Gestionnaire IPAM complet"""
    
    @staticmethod
    def get_next_available_prefix(parent_prefix, prefix_length, vrf=None):
        """
        Trouve le prochain préfixe disponible dans un parent
        """
        try:
            parent_net = ipaddress.ip_network(parent_prefix.prefix)
            used = [ipaddress.ip_network(p.prefix) for p in parent_prefix.prefix_set.all()]
            
            for subnet in parent_net.subnets(new_prefix=prefix_length):
                if not any(subnet.overlaps(u) for u in used):
                    return subnet
            return None
        except Exception as e:
            return None
    
    @staticmethod
    def get_next_available_ip(prefix):
        """
        Trouve la prochaine IP disponible dans un préfixe
        """
        try:
            network = ipaddress.ip_network(prefix.prefix)
            used = set(ipaddress.ip_address(ip.address) for ip in prefix.ipaddress_set.filter(status='active'))
            
            for ip in network.hosts():
                if ip not in used:
                    return ip
            return None
        except Exception as e:
            return None
    
    @staticmethod
    def reserve_prefix(parent_prefix, prefix_length, description="", vrf=None, site=None):
        """Réserve un nouveau préfixe"""
        next_prefix = IPAMManager.get_next_available_prefix(parent_prefix, prefix_length, vrf)
        if next_prefix:
            return Prefix.objects.create(
                prefix=str(next_prefix),
                vrf=vrf or parent_prefix.vrf,
                site=site or parent_prefix.site,
                description=description,
                status='reserved',
                is_pool=True
            )
        return None
    
    @staticmethod
    def reserve_ip(prefix, description="", dns_name="", interface=None):
        """Réserve une nouvelle IP"""
        next_ip = IPAMManager.get_next_available_ip(prefix)
        if next_ip:
            return IPAddress.objects.create(
                address=str(next_ip),
                prefix_length=prefix.prefix_length,
                vrf=prefix.vrf,
                interface=interface,
                description=description,
                dns_name=dns_name,
                status='reserved'
            )
        return None
    
    @staticmethod
    def calculate_usage(prefix):
        """Calcule le taux d'utilisation d'un préfixe"""
        try:
            network = ipaddress.ip_network(prefix.prefix)
            total_ips = network.num_addresses
            used_ips = prefix.ipaddress_set.filter(status='active').count()
            
            if prefix.family == 4 and network.prefixlen < 31:
                # Soustraire réseau et broadcast
                total_ips = max(0, total_ips - 2)
            
            usage_percent = (used_ips / total_ips * 100) if total_ips > 0 else 0
            
            return {
                'total': total_ips,
                'used': used_ips,
                'available': total_ips - used_ips,
                'usage_percent': round(usage_percent, 2)
            }
        except Exception as e:
            return None