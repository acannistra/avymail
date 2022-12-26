import requests
from typing import Optional
from typing import Dict
from os import path

API_BASE="https://api.avalanche.org/v2/public"

class AvalancheAPI():
    def __init__(self):
        self.centers: Optional[Dict] = self.load_centers()
        
    def load_centers(self) -> Dict:
        
        url = API_BASE+"/products/map-layer"
        
        zones = {}
        data = requests.get(
            API_BASE+"/products/map-layer"
        ).json()['features']
        
        zones =  [
            {
                'id': f['id'],
                'center': {
                    'id': f['properties']['center_id'],
                    'name': f['properties']['center']
                },
                'zone_name': f['properties']['name']
            }
            for f in data
        ]

        centers = set([
            (z['center']['name'], z['center']['id']) for z in zones
        ])

        centers = {
            c[0]: {
                'center_id': c[1], 
                'center_name': c[0],
                'zones': []
            } 
            for c in centers
        }

        for z in zones:
            centers[z['center']['name']]['zones'].append({'id': z['id'], 'name': z['zone_name']})


        self.centers = centers