
import json

# Update report.json with the task-specified region bounds
with open('output/report.json') as f:
    report = json.load(f)

# The task specifies the region as lat 60.49-61.69, lon 17.25-18.45
report['region'] = {
    'lat_min': 60.49,
    'lat_max': 61.69,
    'lon_min': 17.25,
    'lon_max': 18.45
}

with open('output/report.json', 'w') as f:
    json.dump(report, f, indent=2)

print("Report updated:")
print(json.dumps(report, indent=2))
