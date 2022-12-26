import requests
from typing import Optional
from typing import Dict
from typing import List
from os import path

API_BASE="https://api.avalanche.org/v2/public"

class APIException(Exception):
    pass

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


        return centers

    def get_zones(self, center: str) -> List:
        try:
            return self.centers[center]['zones']
        except KeyError:
            raise APIException(f"{center} not found.")

    def get_forecast(self, center: str, zone_id: str): 
        center_id = self.centers[center]['center_id']
        _url = API_BASE + f"/product?type=forecast&center_id={center_id}&zone_id={zone_id}"
        return requests.get(_url).json()