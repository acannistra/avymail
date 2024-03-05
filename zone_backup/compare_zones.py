import sys
import json
from pprint import pprint

# This script compares JSON objects from two input files (f1 and f2) and maps the zone IDs based on certain conditions.
# The mapped objects are then printed to the console.

# CLI Usage:
# python compare_zones.py <f1> <f2> <f3>

# <f1>: Path to the older input JSON file
# <f2>: Path to the newer input JSON file
# <f3>: Path to the newline-delimited JSON file to be modified

# Example:
# python compare_zones.py zones_older.json zones_newer.json records.txt


zone_mapping = {}

f1 = sys.argv[1]
f2 = sys.argv[2]
f3 = sys.argv[3]


def compare_json_objects(obj1, obj2):
    if (
        obj1["name"] == obj2["name"]
        and obj1["center_id"] == obj2["center_id"]
        and obj1["zone_id"] != obj2["zone_id"]
    ):
        zone_mapping[str(obj1["zone_id"])] = str(obj2["zone_id"])


with open(f1) as file1, open(f2) as file2, open(f3) as file3:
    data1 = json.load(file1)
    data2 = json.load(file2)

    for obj1 in data1:
        for obj2 in data2:
            compare_json_objects(obj1, obj2)

    for line in file3:
        obj = json.loads(line)
        if obj["zone_id"] in zone_mapping:
            obj["zone_id"] = zone_mapping[obj["zone_id"]]
        print(json.dumps(obj))
