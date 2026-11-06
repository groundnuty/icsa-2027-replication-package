
import json

# Verify report.json
with open('output/report.json', 'r') as f:
    report = json.load(f)

print("Report fields:", list(report.keys()))
print("Region:", report['region'])
print("Baseline:", report['baseline_analysed'])
print("Target:", report['target_analysed'])
print("Events:", report['events'])
print("Complete:", report['complete'])
print("Caveats:", report['caveats'])
