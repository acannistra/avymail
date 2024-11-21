from avalanche import AvalancheAPI
import requests
import pprint

api = AvalancheAPI()

centers = api.load_centers()

center_status = {}


def valid_fcst(fcst):
    return fcst["hazard_discussion"] or (
        fcst["bottom_line"] != None and len(fcst["danger"]) > 0
    )


test_centers = [
    "Wallowa Avalanche Center",
    "Alaska Avalanche Information Center",
    "Coastal Alaska Avalanche Center",
    "Hatcher Pass Avalanche Center",
    "City of Juneau",
    "Northwest Avalanche Center",
]
for c, meta in centers.items():
    zonestatus = {}
    for zinfo in meta["zones"]:
        print(meta["center_id"], zinfo["id"])
        try:
            fcst = api.get_forecast(meta["center_id"], zinfo["id"])
            print("success")
            zonestatus[zinfo["id"]] = "OK"
            if not valid_fcst(fcst):
                zonestatus[zinfo["id"]] = "NOFORECAST"
        except requests.exceptions.JSONDecodeError as e:
            print(e)
            print("fail")
            zonestatus[zinfo["id"]] = "FAIL"
            continue

    center_status[c] = zonestatus

pprint.pp(center_status)
