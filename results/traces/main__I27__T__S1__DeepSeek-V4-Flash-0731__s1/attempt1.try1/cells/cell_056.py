
import json

with open('output/report.json', 'r') as f:
    report = json.load(f)

print(json.dumps(report, indent=2))
print()

# Verify all required fields are present
required_fields = ['region', 'baseline_analysed', 'target_analysed', 'events', 'complete', 'caveats']
for field in required_fields:
    if field in report:
        print(f"✓ {field}: {report[field]}")
    else:
        print(f"✗ Missing field: {field}")
