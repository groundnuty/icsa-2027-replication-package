
import json

# Read current report
with open('output/report.json') as f:
    report = json.load(f)

# Update baseline_analysed to reflect the actual date range used
report['baseline_analysed'] = {
    "start": "1991-12-27",
    "end": "2003-01-05"
}

with open('output/report.json', 'w') as f:
    json.dump(report, f, indent=2)

print("Updated report:")
print(json.dumps(report, indent=2))
