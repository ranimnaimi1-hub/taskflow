# config/settings/jazzmin_settings.py
"""
Jazzmin Admin Settings - Ultra Professional avec Menu Light & Inventory Expandable
Version complète avec intégration Ansible, Terraform, Jenkins, Grafana, EVE-NG et Monitoring
"""

JAZZMIN_SETTINGS = {
    # ========================================================================
    # BRANDING
    # ========================================================================
    "site_title": "NetDevOps Platform",
    "site_header": "NetDevOps Administrator",
    "site_brand": "⚡ NetDevOps",
    "site_logo": None,
    "login_logo": None,
    "site_icon": None,
    "welcome_sign": "🌟 Welcome to NetDevOps Platform - Network Automation & Infrastructure as Code",
    "copyright": "NetDevOps Platform 2026 | v2.0.0",    
    
    # ========================================================================
    # TOP MENU LINKS
    # ========================================================================
    "topmenu_links": [
        {"name": "🏠 Dashboard", "url": "admin:index", "permissions": ["auth.view_user"]},
        {"name": "📊 Analytics", "url": "/admin/analytics/", "new_window": False},
        {"name": "📚 API Docs", "url": "/api/schema/swagger-ui/", "new_window": True},
        {"name": "📖 ReDoc", "url": "/api/schema/redoc/", "new_window": True},
        {"name": "📧 Support", "url": "https://support.netdevops.com", "new_window": True},
    ],
    
    # ========================================================================
    # USER MENU LINKS
    # ========================================================================
    "usermenu_links": [
        {"model": "users.user"},
        {"name": "🔐 My Profile", "url": "/admin/users/user/", "icon": "fas fa-user-circle"},
        {"name": "⚙️ Account Settings", "url": "/admin/account/", "icon": "fas fa-cog"},
        {"name": "📄 Documentation", "url": "https://docs.netdevops.com", "new_window": True},
    ],
    
    # ========================================================================
    # SIDEBAR CONFIGURATION
    # ========================================================================
    "show_sidebar": True,
    "navigation_expanded": False,  # Menu réduit par défaut
    "hide_apps": [],
    "hide_models": [],
    
    # ========================================================================
    # ORDER WITH RESPECT TO - Organisation hiérarchique
    # ========================================================================
    "order_with_respect_to": [
        "users",
        "inventory",
        "ansible_app",
        "terraform_app",
        "jenkins_app",
        "grafana_app",
        "eveng_app",
        "monitoring",      # ✅ Monitoring après EVE-NG
        "core",
        "auth",
        "authtoken",
        "token_blacklist",
    ],
    
    # ========================================================================
    # ICONS - Tous les modèles avec icônes
    # ========================================================================
    "icons": {
        # Auth
        "auth": "fas fa-lock",
        "auth.Group": "fas fa-users-cog",
        
        # Users App
        "users": "fas fa-users",
        "users.User": "fas fa-user-circle",
        "users.Team": "fas fa-users",
        "users.Role": "fas fa-user-tag",
        "users.Permission": "fas fa-key",
        "users.UserActivity": "fas fa-history",
        
        # ====================================================================
        # INVENTORY - App principale
        # ====================================================================
        "inventory": "fas fa-sitemap",
        
        # Hiérarchie
        "inventory.Region": "fas fa-globe-americas",
        "inventory.Site": "fas fa-building",
        "inventory.Location": "fas fa-map-marker-alt",
        
        # Équipements
        "inventory.Manufacturer": "fas fa-industry",
        "inventory.DeviceType": "fas fa-microchip",
        "inventory.Rack": "fas fa-server",
        "inventory.Device": "fas fa-network-wired",
        "inventory.Interface": "fas fa-plug",
        "inventory.PowerPort": "fas fa-bolt",
        "inventory.PowerFeed": "fas fa-charging-station",
        
        # Câblage
        "inventory.Cable": "fas fa-cable-car",
        "inventory.BreakoutCable": "fas fa-code-branch",
        
        # IPAM
        "inventory.VRF": "fas fa-route",
        "inventory.RouteTarget": "fas fa-bullseye",
        "inventory.Prefix": "fas fa-arrows-alt-h",
        "inventory.IPAddress": "fas fa-hashtag",
        
        # VLANs
        "inventory.VLANGroup": "fas fa-layer-group",
        "inventory.VLAN": "fas fa-project-diagram",
        
        # Circuits WAN
        "inventory.Provider": "fas fa-tower-cell",
        "inventory.Circuit": "fas fa-circle-nodes",
        "inventory.CircuitTermination": "fas fa-ethernet",
        
        # Routing
        "inventory.ASN": "fas fa-chart-network",
        "inventory.FHRPGroup": "fas fa-arrows-spin",
        "inventory.BGPSession": "fas fa-code-branch",
        
        # Virtualisation
        "inventory.Cluster": "fas fa-cubes",
        "inventory.VirtualMachine": "fas fa-desktop",
        
        # Tenancy
        "inventory.Tenant": "fas fa-users-between-lines",
        "inventory.Contact": "fas fa-address-card",
        "inventory.TenantAssignment": "fas fa-user-tag",
        
        # L2VPN
        "inventory.L2VPN": "fas fa-merge",
        
        # ====================================================================
        # ANSIBLE APP - Automatisation
        # ====================================================================
        "ansible_app": "fab fa-ansible",
        
        # Inventaires
        "ansible_app.AnsibleInventory": "fas fa-list",
        
        # Playbooks
        "ansible_app.Playbook": "fas fa-file-code",
        "ansible_app.PlaybookExecution": "fas fa-play-circle",
        "ansible_app.PlaybookSchedule": "fas fa-clock",
        
        # Rôles et Collections
        "ansible_app.AnsibleRole": "fas fa-puzzle-piece",
        "ansible_app.AnsibleCollection": "fas fa-layer-group",
        
        # Tâches et Variables
        "ansible_app.AnsibleTask": "fas fa-tasks",
        "ansible_app.AnsibleVars": "fas fa-code-branch",
        
        # Credentials
        "ansible_app.AnsibleCredential": "fas fa-key",
        
        # ====================================================================
        # TERRAFORM APP - Infrastructure as Code
        # ====================================================================
        "terraform_app": "fas fa-cloud",
        
        # Configurations
        "terraform_app.TerraformConfig": "fas fa-file-code",
        "terraform_app.TerraformPlan": "fas fa-clipboard-list",
        "terraform_app.TerraformApply": "fas fa-play-circle",
        "terraform_app.TerraformState": "fas fa-database",
        
        # Modules et Providers
        "terraform_app.TerraformModule": "fas fa-puzzle-piece",
        "terraform_app.TerraformProvider": "fas fa-plug",
        
        # Variables et Credentials
        "terraform_app.TerraformVariable": "fas fa-code-branch",
        "terraform_app.TerraformCredential": "fas fa-key",
        
        # ====================================================================
        # JENKINS APP - CI/CD
        # ====================================================================
        "jenkins_app": "fab fa-jenkins",
        
        # Serveurs
        "jenkins_app.JenkinsServer": "fas fa-server",
        
        # Jobs et Builds
        "jenkins_app.JenkinsJob": "fas fa-code-branch",
        "jenkins_app.JenkinsBuild": "fas fa-hammer",
        "jenkins_app.JenkinsPipeline": "fas fa-code-merge",
        
        # Infrastructure
        "jenkins_app.JenkinsNode": "fas fa-network-wired",
        "jenkins_app.JenkinsPlugin": "fas fa-puzzle-piece",
        
        # Sécurité
        "jenkins_app.JenkinsCredential": "fas fa-key",
        
        # Vues
        "jenkins_app.JenkinsView": "fas fa-eye",
        
        # ====================================================================
        # GRAFANA APP - Monitoring & Visualisation
        # ====================================================================
        "grafana_app": "fas fa-chart-line",
        
        # Serveurs
        "grafana_app.GrafanaServer": "fas fa-server",
        
        # Dashboards
        "grafana_app.GrafanaDashboard": "fas fa-th-large",
        "grafana_app.GrafanaPanel": "fas fa-chart-bar",
        "grafana_app.GrafanaFolder": "fas fa-folder",
        
        # Données
        "grafana_app.GrafanaDatasource": "fas fa-database",
        "grafana_app.GrafanaAlert": "fas fa-exclamation-triangle",
        
        # Organisations et Utilisateurs
        "grafana_app.GrafanaOrganization": "fas fa-building",
        "grafana_app.GrafanaUser": "fas fa-user",
        "grafana_app.GrafanaTeam": "fas fa-users",
        
        # Snapshots
        "grafana_app.GrafanaSnapshot": "fas fa-camera",
        
        # ====================================================================
        # EVE-NG APP - Network Emulation
        # ====================================================================
        "eveng_app": "fas fa-flask",
        
        # Serveurs
        "eveng_app.EVENServer": "fas fa-server",
        
        # Laboratoires
        "eveng_app.EVENLab": "fas fa-vial",
        "eveng_app.EVENNode": "fas fa-microchip",
        "eveng_app.EVENNetwork": "fas fa-project-diagram",
        "eveng_app.EVENLink": "fas fa-link",
        
        # Images
        "eveng_app.EVENImage": "fas fa-database",
        
        # Sessions
        "eveng_app.EVENUserSession": "fas fa-user-clock",
        
        # ====================================================================
        # MONITORING APP - Platform Monitoring
        # ====================================================================
        "monitoring": "fas fa-heartbeat",
        
        # Métriques
        "monitoring.SystemMetric": "fas fa-microchip",
        "monitoring.DeviceMetric": "fas fa-server",
        "monitoring.InterfaceMetric": "fas fa-plug",
        "monitoring.ApplicationMetric": "fas fa-chart-line",
        
        # Alertes
        "monitoring.Alert": "fas fa-exclamation-triangle",
        "monitoring.AlertThreshold": "fas fa-sliders-h",
        
        # Notifications
        "monitoring.NotificationChannel": "fas fa-bell",
        "monitoring.NotificationLog": "fas fa-history",
        
        # Dashboards
        "monitoring.Dashboard": "fas fa-tachometer-alt",
        "monitoring.MetricCollection": "fas fa-layer-group",
        
        # ====================================================================
        # AUTRES APPS
        # ====================================================================
        "core": "fas fa-cog",
        "core.Setting": "fas fa-sliders-h",
        
        # Auth Token
        "authtoken": "fas fa-key",
        "authtoken.Token": "fas fa-token",
        "authtoken.tokenproxy": "fas fa-key",
        
        # Token Blacklist
        "token_blacklist": "fas fa-ban",
        "token_blacklist.BlacklistedToken": "fas fa-ban",
        "token_blacklist.OutstandingToken": "fas fa-clock",
    },
    
    # ========================================================================
    # DEFAULT ICONS
    # ========================================================================
    "default_icon_parents": "fas fa-folder-open",
    "default_icon_children": "fas fa-file",
    
    # ========================================================================
    # CUSTOM LINKS - Liens rapides dans le menu
    # ========================================================================
    "custom_links": {
        "inventory": [
            {
                "name": "📊 Dashboard",
                "url": "/admin/inventory/dashboard/",
                "icon": "fas fa-chart-pie",
                "permissions": ["inventory.view_device"]
            },
            {
                "name": "📍 Sites Map",
                "url": "/admin/inventory/site/map/",
                "icon": "fas fa-map",
                "permissions": ["inventory.view_site"]
            },
            {
                "name": "🌐 IPAM Overview",
                "url": "/admin/inventory/ipaddress/overview/",
                "icon": "fas fa-globe",
                "permissions": ["inventory.view_ipaddress"]
            },
            {
                "name": "🔌 Cabling Topology",
                "url": "/admin/inventory/cable/topology/",
                "icon": "fas fa-code-branch",
                "permissions": ["inventory.view_cable"]
            },
        ],
        "ansible_app": [
            {
                "name": "🚀 Execute Playbook",
                "url": "/admin/ansible_app/playbook/add/",
                "icon": "fas fa-play-circle",
                "permissions": ["ansible_app.execute_playbook"]
            },
            {
                "name": "📋 Inventory Manager",
                "url": "/admin/ansible_app/ansibleinventory/",
                "icon": "fas fa-list",
                "permissions": ["ansible_app.view_ansibleinventory"]
            },
            {
                "name": "⏰ Scheduled Jobs",
                "url": "/admin/ansible_app/playbookschedule/",
                "icon": "fas fa-clock",
                "permissions": ["ansible_app.view_playbookschedule"]
            },
            {
                "name": "📊 Execution History",
                "url": "/admin/ansible_app/playbookexecution/",
                "icon": "fas fa-history",
                "permissions": ["ansible_app.view_playbookexecution"]
            },
        ],
        "terraform_app": [
            {
                "name": "📋 New Configuration",
                "url": "/admin/terraform_app/terraformconfig/add/",
                "icon": "fas fa-plus-circle",
                "permissions": ["terraform_app.add_terraformconfig"]
            },
            {
                "name": "🚀 Execute Plan",
                "url": "/admin/terraform_app/terraformconfig/",
                "icon": "fas fa-play-circle",
                "permissions": ["terraform_app.view_terraformconfig"]
            },
            {
                "name": "📊 Apply History",
                "url": "/admin/terraform_app/terraformapply/",
                "icon": "fas fa-history",
                "permissions": ["terraform_app.view_terraformapply"]
            },
            {
                "name": "🔑 Credentials",
                "url": "/admin/terraform_app/terraformcredential/",
                "icon": "fas fa-key",
                "permissions": ["terraform_app.view_terraformcredential"]
            },
            {
                "name": "📦 Modules",
                "url": "/admin/terraform_app/terraformmodule/",
                "icon": "fas fa-puzzle-piece",
                "permissions": ["terraform_app.view_terraformmodule"]
            },
        ],
        "jenkins_app": [
            {
                "name": "➕ Add Server",
                "url": "/admin/jenkins_app/jenkinsserver/add/",
                "icon": "fas fa-plus-circle",
                "permissions": ["jenkins_app.add_jenkinsserver"]
            },
            {
                "name": "🚀 Trigger Build",
                "url": "/admin/jenkins_app/jenkinsjob/",
                "icon": "fas fa-play-circle",
                "permissions": ["jenkins_app.view_jenkinsjob"]
            },
            {
                "name": "📊 Build History",
                "url": "/admin/jenkins_app/jenkinsbuild/",
                "icon": "fas fa-history",
                "permissions": ["jenkins_app.view_jenkinsbuild"]
            },
            {
                "name": "🔧 Nodes",
                "url": "/admin/jenkins_app/jenkinsnode/",
                "icon": "fas fa-network-wired",
                "permissions": ["jenkins_app.view_jenkinsnode"]
            },
            {
                "name": "🔌 Plugins",
                "url": "/admin/jenkins_app/jenkinsplugin/",
                "icon": "fas fa-puzzle-piece",
                "permissions": ["jenkins_app.view_jenkinsplugin"]
            },
            {
                "name": "🔑 Credentials",
                "url": "/admin/jenkins_app/jenkinscredential/",
                "icon": "fas fa-key",
                "permissions": ["jenkins_app.view_jenkinscredential"]
            },
        ],
        "grafana_app": [
            {
                "name": "➕ Add Server",
                "url": "/admin/grafana_app/grafanaserver/add/",
                "icon": "fas fa-plus-circle",
                "permissions": ["grafana_app.add_grafanaserver"]
            },
            {
                "name": "📊 View Dashboards",
                "url": "/admin/grafana_app/grafanadashboard/",
                "icon": "fas fa-th-large",
                "permissions": ["grafana_app.view_grafanadashboard"]
            },
            {
                "name": "📈 Datasources",
                "url": "/admin/grafana_app/grafanadatasource/",
                "icon": "fas fa-database",
                "permissions": ["grafana_app.view_grafanadatasource"]
            },
            {
                "name": "⚠️ Alerts",
                "url": "/admin/grafana_app/grafanaalert/",
                "icon": "fas fa-exclamation-triangle",
                "permissions": ["grafana_app.view_grafanaalert"]
            },
            {
                "name": "👥 Users",
                "url": "/admin/grafana_app/grafanauser/",
                "icon": "fas fa-user",
                "permissions": ["grafana_app.view_grafanauser"]
            },
            {
                "name": "📸 Snapshots",
                "url": "/admin/grafana_app/grafanasnapshot/",
                "icon": "fas fa-camera",
                "permissions": ["grafana_app.view_grafanasnapshot"]
            },
        ],
        "eveng_app": [
            {
                "name": "➕ Add Server",
                "url": "/admin/eveng_app/evenserver/add/",
                "icon": "fas fa-plus-circle",
                "permissions": ["eveng_app.add_evenserver"]
            },
            {
                "name": "🧪 View Labs",
                "url": "/admin/eveng_app/evenlab/",
                "icon": "fas fa-flask",
                "permissions": ["eveng_app.view_evenlab"]
            },
            {
                "name": "🔧 Nodes",
                "url": "/admin/eveng_app/evennode/",
                "icon": "fas fa-microchip",
                "permissions": ["eveng_app.view_evennode"]
            },
            {
                "name": "🌐 Networks",
                "url": "/admin/eveng_app/evennetwork/",
                "icon": "fas fa-project-diagram",
                "permissions": ["eveng_app.view_evennetwork"]
            },
            {
                "name": "🔗 Links",
                "url": "/admin/eveng_app/evenlink/",
                "icon": "fas fa-link",
                "permissions": ["eveng_app.view_evenlink"]
            },
            {
                "name": "📦 Images",
                "url": "/admin/eveng_app/evenimage/",
                "icon": "fas fa-database",
                "permissions": ["eveng_app.view_evenimage"]
            },
            {
                "name": "👤 Sessions",
                "url": "/admin/eveng_app/evenusersession/",
                "icon": "fas fa-user-clock",
                "permissions": ["eveng_app.view_evenusersession"]
            },
        ],
        "monitoring": [
            {
                "name": "📊 System Metrics",
                "url": "/admin/monitoring/systemmetric/",
                "icon": "fas fa-microchip",
                "permissions": ["monitoring.view_systemmetric"]
            },
            {
                "name": "📈 Device Metrics",
                "url": "/admin/monitoring/devicemetric/",
                "icon": "fas fa-server",
                "permissions": ["monitoring.view_devicemetric"]
            },
            {
                "name": "🔌 Interface Metrics",
                "url": "/admin/monitoring/interfacemetric/",
                "icon": "fas fa-plug",
                "permissions": ["monitoring.view_interfacemetric"]
            },
            {
                "name": "⚠️ Alerts",
                "url": "/admin/monitoring/alert/",
                "icon": "fas fa-exclamation-triangle",
                "permissions": ["monitoring.view_alert"]
            },
            {
                "name": "⚙️ Thresholds",
                "url": "/admin/monitoring/alertthreshold/",
                "icon": "fas fa-sliders-h",
                "permissions": ["monitoring.view_alertthreshold"]
            },
            {
                "name": "🔔 Notifications",
                "url": "/admin/monitoring/notificationchannel/",
                "icon": "fas fa-bell",
                "permissions": ["monitoring.view_notificationchannel"]
            },
            {
                "name": "📊 Dashboards",
                "url": "/admin/monitoring/dashboard/",
                "icon": "fas fa-tachometer-alt",
                "permissions": ["monitoring.view_dashboard"]
            },
        ],
    },
    
    # ========================================================================
    # RELATED MODAL
    # ========================================================================
    "related_modal_active": True,
    
    # ========================================================================
    # CUSTOM CSS/JS
    # ========================================================================
    "custom_css": "css/custom_admin.css",
    "custom_js": "js/custom_admin.js",
    "show_ui_builder": False,
    
    # ========================================================================
    # CHANGE FORM FORMAT
    # ========================================================================
    "changeform_format": "horizontal_tabs",
    "changeform_format_overrides": {
        "users.user": "collapsible",
        "inventory.device": "horizontal_tabs",
        "inventory.site": "vertical_tabs",
        "inventory.rack": "carousel",
        "inventory.prefix": "horizontal_tabs",
        "inventory.circuit": "vertical_tabs",
        "inventory.cluster": "horizontal_tabs",
        "ansible_app.playbook": "horizontal_tabs",
        "ansible_app.ansibleinventory": "vertical_tabs",
        "terraform_app.terraformconfig": "horizontal_tabs",
        "terraform_app.terraformplan": "collapsible",
        "terraform_app.terraformapply": "collapsible",
        "terraform_app.terraformstate": "collapsible",
        "terraform_app.terraformcredential": "vertical_tabs",
        "jenkins_app.jenkinsserver": "horizontal_tabs",
        "jenkins_app.jenkinsjob": "vertical_tabs",
        "jenkins_app.jenkinsbuild": "collapsible",
        "jenkins_app.jenkinsnode": "collapsible",
        "jenkins_app.jenkinsplugin": "collapsible",
        "jenkins_app.jenkinscredential": "vertical_tabs",
        "jenkins_app.jenkinsview": "collapsible",
        "jenkins_app.jenkinspipeline": "horizontal_tabs",
        "grafana_app.grafanaserver": "horizontal_tabs",
        "grafana_app.grafanadashboard": "vertical_tabs",
        "grafana_app.grafanadatasource": "collapsible",
        "grafana_app.grafanaalert": "collapsible",
        "grafana_app.grafanaorganization": "collapsible",
        "grafana_app.grafanauser": "vertical_tabs",
        "grafana_app.grafanafolder": "collapsible",
        "grafana_app.grafanapanel": "collapsible",
        "grafana_app.grafanasnapshot": "collapsible",
        "grafana_app.grafanateam": "collapsible",
        "eveng_app.evenserver": "horizontal_tabs",
        "eveng_app.evenlab": "vertical_tabs",
        "eveng_app.evennode": "collapsible",
        "eveng_app.evennetwork": "collapsible",
        "eveng_app.evenlink": "collapsible",
        "eveng_app.evenimage": "collapsible",
        "eveng_app.evenusersession": "collapsible",
        "monitoring.systemmetric": "collapsible",
        "monitoring.devicemetric": "collapsible",
        "monitoring.interfacemetric": "collapsible",
        "monitoring.applicationmetric": "collapsible",
        "monitoring.alert": "horizontal_tabs",
        "monitoring.alertthreshold": "collapsible",
        "monitoring.notificationchannel": "collapsible",
        "monitoring.notificationlog": "collapsible",
        "monitoring.dashboard": "horizontal_tabs",
        "monitoring.metriccollection": "collapsible",
    },
    
    # ========================================================================
    # LANGUAGE - Désactivé pour éviter l'erreur
    # ========================================================================
    "language_chooser": False,
}

# ========================================================================
# JAZZMIN UI TWEAKS - Thème LIGHT professionnel
# ========================================================================
JAZZMIN_UI_TWEAKS = {
    # Theme - Light professionnel
    "theme": "flatly",
    "dark_mode_theme": "darkly",
    
    # Navbar - Light avec ombre subtile
    "navbar_small_text": False,
    "navbar_fixed": True,
    "navbar": "navbar-light bg-white",
    "navbar_class": "shadow-sm border-bottom",
    
    # Sidebar - Light avec séparation claire
    "sidebar": "sidebar-light-primary",
    "sidebar_fixed": True,
    "sidebar_nav_small_text": False,
    "sidebar_disable_expand": False,
    "sidebar_nav_child_indent": True,
    "sidebar_nav_compact_style": False,
    "sidebar_nav_legacy_style": False,
    "sidebar_nav_flat_style": True,
    
    # Footer
    "footer_fixed": False,
    "footer_small_text": True,
    
    # Brand
    "brand_small_text": False,
    "brand_colour": "navbar-light",
    "brand_colour_bg": "bg-white",
    
    # Body
    "body_small_text": False,
    "no_navbar_border": False,
    "layout_boxed": False,
    "accent": "accent-primary",
    
    # Buttons - Style moderne
    "button_classes": {
        "primary": "btn-primary btn-sm",
        "secondary": "btn-secondary btn-sm",
        "info": "btn-info btn-sm",
        "warning": "btn-warning btn-sm",
        "danger": "btn-danger btn-sm",
        "success": "btn-success btn-sm",
        "outline-primary": "btn-outline-primary btn-sm",
    },
    
    # Actions
    "actions_sticky_top": True,
}

# ========================================================================
# CUSTOM DASHBOARD
# ========================================================================
JAZZMIN_DASHBOARD = {
    "welcome_message": """
        <div class="alert alert-primary alert-dismissible fade show" role="alert">
            <strong>👋 Welcome back, {user}!</strong>
            <span class="badge bg-warning ms-2">{pending_alerts} pending alerts</span>
            <span class="badge bg-success ms-2">{active_devices} active devices</span>
            <span class="badge bg-info ms-2">{free_ips} free IPs</span>
            <span class="badge bg-primary ms-2">{terraform_configs} Terraform configs</span>
            <span class="badge bg-danger ms-2">{jenkins_builds} Jenkins builds</span>
            <span class="badge bg-info ms-2">{grafana_dashboards} Grafana dashboards</span>
            <span class="badge bg-purple ms-2">{eveng_labs} EVE-NG labs</span>
            <span class="badge bg-success ms-2">{active_alerts} Active Alerts</span>
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    """,
    
    "quick_actions": [
        {"name": "➕ Add Device", "url": "/admin/inventory/device/add/", "icon": "fas fa-plus-circle", "color": "success"},
        {"name": "📍 Add Site", "url": "/admin/inventory/site/add/", "icon": "fas fa-building", "color": "primary"},
        {"name": "🌐 Add IP", "url": "/admin/inventory/ipaddress/add/", "icon": "fas fa-globe", "color": "info"},
        {"name": "🔌 Add Cable", "url": "/admin/inventory/cable/add/", "icon": "fas fa-cable-car", "color": "warning"},
        {"name": "📡 Add Circuit", "url": "/admin/inventory/circuit/add/", "icon": "fas fa-satellite-dish", "color": "danger"},
        {"name": "💻 Add VM", "url": "/admin/inventory/virtualmachine/add/", "icon": "fas fa-desktop", "color": "secondary"},
        {"name": "🚀 Execute Playbook", "url": "/admin/ansible_app/playbook/add/", "icon": "fas fa-play-circle", "color": "info"},
        {"name": "📋 New Inventory", "url": "/admin/ansible_app/ansibleinventory/add/", "icon": "fas fa-list", "color": "success"},
        {"name": "🏗️ Terraform Config", "url": "/admin/terraform_app/terraformconfig/add/", "icon": "fas fa-cloud", "color": "primary"},
        {"name": "📦 Terraform Plan", "url": "/admin/terraform_app/terraformplan/", "icon": "fas fa-clipboard-list", "color": "warning"},
        {"name": "🔧 Jenkins Server", "url": "/admin/jenkins_app/jenkinsserver/add/", "icon": "fab fa-jenkins", "color": "danger"},
        {"name": "⚡ Trigger Build", "url": "/admin/jenkins_app/jenkinsjob/", "icon": "fas fa-play-circle", "color": "info"},
        {"name": "📊 New Dashboard", "url": "/admin/grafana_app/grafanadashboard/add/", "icon": "fas fa-chart-line", "color": "info"},
        {"name": "📈 Add Datasource", "url": "/admin/grafana_app/grafanadatasource/add/", "icon": "fas fa-database", "color": "success"},
        {"name": "🧪 New Lab", "url": "/admin/eveng_app/evenlab/add/", "icon": "fas fa-flask", "color": "purple"},
        {"name": "🔧 Add Node", "url": "/admin/eveng_app/evennode/add/", "icon": "fas fa-microchip", "color": "info"},
        {"name": "⚠️ Create Alert", "url": "/admin/monitoring/alert/add/", "icon": "fas fa-exclamation-triangle", "color": "danger"},
        {"name": "📊 System Metrics", "url": "/admin/monitoring/systemmetric/", "icon": "fas fa-microchip", "color": "info"},
    ],
    
    "stats_cards": [
        {"title": "Total Devices", "value": "{device_count}", "icon": "fas fa-server", "color": "primary"},
        {"title": "Active Playbooks", "value": "{playbook_count}", "icon": "fab fa-ansible", "color": "danger"},
        {"title": "IP Usage", "value": "{ip_usage}%", "icon": "fas fa-globe", "color": "success"},
        {"title": "Executions (24h)", "value": "{execution_count}", "icon": "fas fa-play-circle", "color": "warning"},
        {"title": "Terraform Configs", "value": "{terraform_configs}", "icon": "fas fa-cloud", "color": "info"},
        {"title": "Terraform Applies", "value": "{terraform_applies}", "icon": "fas fa-check-circle", "color": "primary"},
        {"title": "Jenkins Builds", "value": "{jenkins_builds}", "icon": "fab fa-jenkins", "color": "danger"},
        {"title": "Jenkins Jobs", "value": "{jenkins_jobs}", "icon": "fas fa-code-branch", "color": "warning"},
        {"title": "Grafana Dashboards", "value": "{grafana_dashboards}", "icon": "fas fa-chart-line", "color": "info"},
        {"title": "Active Alerts", "value": "{grafana_alerts}", "icon": "fas fa-exclamation-triangle", "color": "danger"},
        {"title": "EVE-NG Labs", "value": "{eveng_labs}", "icon": "fas fa-flask", "color": "purple"},
        {"title": "Running Nodes", "value": "{eveng_nodes}", "icon": "fas fa-microchip", "color": "success"},
        {"title": "System CPU", "value": "{system_cpu}%", "icon": "fas fa-microchip", "color": "info"},
        {"title": "System Memory", "value": "{system_memory}%", "icon": "fas fa-memory", "color": "warning"},
        {"title": "Active Alerts", "value": "{monitoring_alerts}", "icon": "fas fa-exclamation-triangle", "color": "danger"},
    ],
    
    "recent_activities": {
        "title": "📋 Recent Activities",
        "limit": 10,
        "model": "users.UserActivity",
        "fields": ["user", "action", "created_at"],
    },
    
    "charts": {
        "device_types": {
            "title": "Device Distribution by Type",
            "type": "pie",
            "data_url": "/api/v1/stats/device-types/",
        },
        "playbook_executions": {
            "title": "Playbook Executions (7 days)",
            "type": "line",
            "data_url": "/api/v1/stats/playbook-executions/",
        },
        "ip_usage": {
            "title": "IP Address Usage by VRF",
            "type": "bar",
            "data_url": "/api/v1/stats/ip-usage/",
        },
        "terraform_applies": {
            "title": "Terraform Applies (7 days)",
            "type": "line",
            "data_url": "/api/v1/stats/terraform-applies/",
        },
        "jenkins_builds": {
            "title": "Jenkins Builds (7 days)",
            "type": "line",
            "data_url": "/api/v1/stats/jenkins-builds/",
        },
        "grafana_alerts": {
            "title": "Grafana Alerts by State",
            "type": "pie",
            "data_url": "/api/v1/stats/grafana-alerts/",
        },
        "grafana_datasources": {
            "title": "Datasources by Type",
            "type": "bar",
            "data_url": "/api/v1/stats/grafana-datasources/",
        },
        "eveng_labs": {
            "title": "EVE-NG Labs by Status",
            "type": "pie",
            "data_url": "/api/v1/stats/eveng-labs/",
        },
        "eveng_nodes": {
            "title": "EVE-NG Nodes by Type",
            "type": "bar",
            "data_url": "/api/v1/stats/eveng-nodes/",
        },
        "system_metrics": {
            "title": "System Metrics (24h)",
            "type": "line",
            "data_url": "/api/v1/stats/system-metrics/",
        },
        "alert_severity": {
            "title": "Alerts by Severity",
            "type": "pie",
            "data_url": "/api/v1/stats/alert-severity/",
        },
    },
}