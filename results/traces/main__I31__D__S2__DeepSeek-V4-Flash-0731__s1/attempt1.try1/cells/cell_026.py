
import json

# Update report.json
with open('output/report.json', 'r') as f:
    report = json.load(f)

report['baseline_analysed'] = {"start": "1992-01-01", "end": "2002-12-31"}

with open('output/report.json', 'w') as f:
    json.dump(report, f, indent=2)

print(json.dumps(report, indent=2))
