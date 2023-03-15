import requests
from typing import Optional
from typing import Dict
from typing import List
from os import path

API_BASE = "https://api.avalanche.org/v2/public"


class APIException(Exception):
    pass


class AvalancheAPI:
    def __init__(self):
        self.centers: Optional[Dict] = self.load_centers()

    def load_centers(self) -> Dict:

        url = API_BASE + "/products/map-layer"

        zones: List[dict] = []
        data: list = requests.get(API_BASE + "/products/map-layer").json()["features"]

        zones = [
            {
                "id": f["id"],
                "center": {
                    "id": f["properties"]["center_id"],
                    "name": f["properties"]["center"],
                },
                "zone_name": f["properties"]["name"],
            }
            for f in data
        ]

        centers = set([(z["center"]["name"], z["center"]["id"]) for z in zones])

        centers_dict = {
            c[0]: {"center_id": c[1], "center_name": c[0], "zones": []} for c in centers
        }

        for z in zones:
            centers_dict[z["center"]["name"]]["zones"].append(
                {"id": z["id"], "name": z["zone_name"]}
            )

        return centers_dict

    def get_zones(self, center: str) -> List:
        try:
            return self.centers[center]["zones"]
        except KeyError:
            raise APIException(f"{center} not found.")

    def get_center_meta(self, center_id: str) -> Dict:
        _url = API_BASE + f"/avalanche-center/{center_id}"
        return requests.get(_url).json()

    def get_forecast(self, center_id: str, zone_id: str):
        _url = (
            API_BASE + f"/product?type=forecast&center_id={center_id}&zone_id={zone_id}"
        )
        return requests.get(_url).json()
