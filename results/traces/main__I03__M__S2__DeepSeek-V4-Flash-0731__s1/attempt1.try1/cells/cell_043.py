
import json

with open('output/report.json', 'r') as f:
    report = json.load(f)

# Verify region bounds
print("Region:", report['region'])
print("Expected: lat 54.17 to 55.37, lon 13.25 to 14.45")

# Verify events format
for e in report['events']:
    print(f"  Event: onset={e['onset']}, end={e['end']}")
    assert 'onset' in e and 'end' in e
    # Verify date format
    from datetime import date
    date.fromisoformat(e['onset'])
    date.fromisoformat(e['end'])

# Verify baseline_analysed format
print("\nBaseline:", report['baseline_analysed'])
from datetime import date
date.fromisoformat(report['baseline_analysed']['start'])
date.fromisoformat(report['baseline_analysed']['end'])

# Verify target_analysed format
print("Target:", report['target_analysed'])
date.fromisoformat(report['target_analysed']['start'])
date.fromisoformat(report['target_analysed']['end'])

# Verify complete is bool
print("Complete:", report['complete'], type(report['complete']))

# Verify caveats is string
print("Caveats:", report['caveats'], type(report['caveats']))

print("\nAll checks passed!")
