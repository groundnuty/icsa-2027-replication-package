
import json

with open('output/report.json', 'r') as f:
    report = json.load(f)

print(json.dumps(report, indent=2))
