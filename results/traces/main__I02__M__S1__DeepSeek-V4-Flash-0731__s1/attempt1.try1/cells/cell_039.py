
import json

# Check report.json
with open('output/report.json', 'r') as f:
    report = json.load(f)

print("Report fields:", list(report.keys()))
print("Region:", report['region'])
print("Baseline analysed:", report['baseline_analysed'])
print("Target analysed:", report['target_analysed'])
print("Events:", report['events'])
print("Complete:", report['complete'])
print("Caveats:", report['caveats'])

# Check required fields exist
required = ['region', 'baseline_analysed', 'target_analysed', 'events', 'complete', 'caveats']
for field in required:
    if field not in report:
        print(f"ERROR: Missing field {field}")
    else:
        print(f"OK: {field} present")
