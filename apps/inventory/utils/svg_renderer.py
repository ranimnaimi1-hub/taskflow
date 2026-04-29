# apps/inventory/utils/svg_renderer.py
"""
SVG Renderer - Génération d'élévations de racks
"""
import xml.etree.ElementTree as ET
from ..models import Rack, Device


class SVGRackRenderer:
    """Rendu SVG pour les élévations de racks"""
    
    def __init__(self, rack):
        self.rack = rack
        self.svg = None
        self.u_height = rack.height_u
        self.unit_height = 25  # pixels par U
        self.unit_width = 220  # pixels de largeur
        self.margin_left = 60
        self.margin_top = 30
    
    def render(self):
        """Génère le SVG complet"""
        # Créer le document SVG
        self.svg = ET.Element('svg', {
            'xmlns': 'http://www.w3.org/2000/svg',
            'width': str(self.unit_width + self.margin_left + 20),
            'height': str(self.u_height * self.unit_height + self.margin_top + 30),
            'viewBox': f'0 0 {self.unit_width + self.margin_left + 20} {self.u_height * self.unit_height + self.margin_top + 30}'
        })
        
        # Ajouter le style
        style = ET.SubElement(self.svg, 'style')
        style.text = """
            .rack-frame { fill: #f8f9fa; stroke: #495057; stroke-width: 2; }
            .rack-unit-line { stroke: #adb5bd; stroke-width: 1; stroke-dasharray: 5,3; }
            .rack-unit-text { font-family: monospace; font-size: 10px; fill: #6c757d; }
            .device-rect { fill: #4dabf7; stroke: #1971c2; stroke-width: 1; rx: 3; ry: 3; }
            .device-rect:hover { fill: #3b8ed9; cursor: pointer; }
            .device-text { font-family: sans-serif; font-size: 9px; fill: white; }
            .title-text { font-family: sans-serif; font-size: 16px; font-weight: bold; fill: #212529; }
            .info-text { font-family: sans-serif; font-size: 10px; fill: #495057; }
        """
        
        self._add_background()
        self._add_units()
        self._add_devices()
        self._add_labels()
        
        return ET.tostring(self.svg, encoding='unicode')
    
    def _add_background(self):
        """Ajoute le fond du rack"""
        # Cadre du rack
        ET.SubElement(self.svg, 'rect', {
            'class': 'rack-frame',
            'x': str(self.margin_left - 5), 'y': str(self.margin_top - 5),
            'width': str(self.unit_width + 10),
            'height': str(self.u_height * self.unit_height + 10),
            'rx': '5', 'ry': '5'
        })
        
        # Montants
        ET.SubElement(self.svg, 'line', {
            'x1': str(self.margin_left), 'y1': str(self.margin_top),
            'x2': str(self.margin_left), 'y2': str(self.margin_top + self.u_height * self.unit_height),
            'stroke': '#495057', 'stroke-width': '2'
        })
        ET.SubElement(self.svg, 'line', {
            'x1': str(self.margin_left + self.unit_width), 'y1': str(self.margin_top),
            'x2': str(self.margin_left + self.unit_width), 'y2': str(self.margin_top + self.u_height * self.unit_height),
            'stroke': '#495057', 'stroke-width': '2'
        })
    
    def _add_units(self):
        """Ajoute les divisions par U"""
        for u in range(self.u_height):
            y = self.margin_top + (self.u_height - u - 1) * self.unit_height
            
            # Ligne de séparation
            ET.SubElement(self.svg, 'line', {
                'class': 'rack-unit-line',
                'x1': str(self.margin_left), 'y1': str(y),
                'x2': str(self.margin_left + self.unit_width), 'y2': str(y)
            })
            
            # Label U
            text = ET.SubElement(self.svg, 'text', {
                'class': 'rack-unit-text',
                'x': str(self.margin_left - 25), 'y': str(y + self.unit_height/2 + 3),
                'text-anchor': 'end'
            })
            text.text = f"U{u+1}"
    
    def _add_devices(self):
        """Ajoute les équipements dans le rack"""
        devices = Device.objects.filter(rack=self.rack).order_by('rack_position')
        
        for device in devices:
            if device.rack_position:
                # Calculer la position Y (les U sont numérotés du bas vers le haut)
                y_start = self.margin_top + (self.u_height - device.rack_position - device.device_type.rack_units + 1) * self.unit_height
                height = device.device_type.rack_units * self.unit_height - 2
                
                # Rectangle de l'équipement
                rect = ET.SubElement(self.svg, 'rect', {
                    'class': 'device-rect',
                    'x': str(self.margin_left + 2), 'y': str(y_start + 1),
                    'width': str(self.unit_width - 4),
                    'height': str(height),
                    'data-device-id': str(device.id)
                })
                
                # Nom de l'équipement (tronqué si nécessaire)
                device_name = device.name[:15] + '...' if len(device.name) > 15 else device.name
                text = ET.SubElement(self.svg, 'text', {
                    'class': 'device-text',
                    'x': str(self.margin_left + self.unit_width/2), 'y': str(y_start + height/2 + 4),
                    'text-anchor': 'middle',
                    'dominant-baseline': 'middle'
                })
                text.text = device_name
    
    def _add_labels(self):
        """Ajoute les labels"""
        # Titre
        title = ET.SubElement(self.svg, 'text', {
            'class': 'title-text',
            'x': str(self.margin_left + self.unit_width/2), 'y': '20',
            'text-anchor': 'middle'
        })
        title.text = f"Rack: {self.rack.name}"
        
        # Informations
        info_y = self.margin_top + self.u_height * self.unit_height + 20
        info = ET.SubElement(self.svg, 'text', {
            'class': 'info-text',
            'x': str(self.margin_left), 'y': str(info_y)
        })
        info.text = f"Site: {self.rack.site.name} | Type: {self.rack.get_rack_type_display()} | {self.rack.height_u}U"
        
        # Légende
        legend_x = self.margin_left + self.unit_width + 10
        legend_y = self.margin_top + 20
        
        legend_title = ET.SubElement(self.svg, 'text', {
            'class': 'info-text',
            'x': str(legend_x), 'y': str(legend_y),
            'font-weight': 'bold'
        })
        legend_title.text = "Légende:"
        
        devices_count = Device.objects.filter(rack=self.rack).count()
        free_u = self.rack.height_u - sum(d.device_type.rack_units for d in Device.objects.filter(rack=self.rack))
        
        legend_items = [
            f"Équipements: {devices_count}",
            f"U libres: {free_u}",
            f"Capacité: {self.rack.height_u}U",
            f"Utilisation: {((self.rack.height_u - free_u) / self.rack.height_u * 100):.0f}%"
        ]
        
        for i, item in enumerate(legend_items):
            text = ET.SubElement(self.svg, 'text', {
                'class': 'info-text',
                'x': str(legend_x), 'y': str(legend_y + 20 + i * 15)
            })
            text.text = item