
import json
import os

# Regional events
events_list = [
    {"onset": "2019-06-06", "end": "2019-07-01"},
    {"onset": "2019-07-20", "end": "2019-07-29"}
]

report = {
    "region": {
        "lat_min": 64.39,
        "lat_max": 65.59,
        "lon_min": 23.41,
        "lon_max": 24.61
    },
    "baseline_analysed": {
        "start": "1991-12-27",
        "end": "2003-01-05"
    },
    "target_analysed": {
        "start": "2019-06-01",
        "end": "2019-08-31"
    },
    "events": events_list,
    "complete": True,
    "caveats": ""
}

# Write report
os.makedirs('output', exist_ok=True)
with open('output/report.json', 'w') as f:
    json.dump(report, f, indent=2)

print("Wrote output/report.json")
print(json.dumps(report, indent=2))

# Verify
with open('output/report.json', 'r') as f:
    check = json.load(f)
print("\nVerification:")
print("  Fields:", sorted(check.keys()))
print("  Region:", check["region"])
print("  Baseline:", check["baseline_analysed"])
print("  Target:", check["target_analysed"])
print("  Events:", check["events"])
print("  Complete:", check["complete"])
