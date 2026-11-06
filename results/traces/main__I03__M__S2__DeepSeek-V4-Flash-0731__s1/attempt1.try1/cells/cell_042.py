
import json

with open('output/report.json', 'r') as f:
    report = json.load(f)

required_fields = {'region', 'baseline_analysed', 'target_analysed', 'events', 'complete', 'caveats'}
actual_fields = set(report.keys())
print("Required fields:", required_fields)
print("Actual fields:", actual_fields)
print("Match:", required_fields == actual_fields)
print("Missing:", required_fields - actual_fields)
print("Extra:", actual_fields - required_fields)
