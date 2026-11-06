
import json

with open('output/report.json', 'r') as f:
    report = json.load(f)

print("Report fields:", sorted(report.keys()))
print("Expected fields: region, baseline_analysed, target_analysed, events, complete, caveats")
print("All fields present:", all(k in report for k in ['region', 'baseline_analysed', 'target_analysed', 'events', 'complete', 'caveats']))
print("No extra fields:", sorted(report.keys()) == sorted(['region', 'baseline_analysed', 'target_analysed', 'events', 'complete', 'caveats']))

# Check types
print(f"region type: {type(report['region']).__name__}")
print(f"baseline_analysed type: {type(report['baseline_analysed']).__name__}")
print(f"target_analysed type: {type(report['target_analysed']).__name__}")
print(f"events type: {type(report['events']).__name__}")
print(f"complete type: {type(report['complete']).__name__}")
print(f"caveats type: {type(report['caveats']).__name__}")

# Check region values
print(f"region: {report['region']}")
# Check baseline_analysed values
print(f"baseline_analysed: {report['baseline_analysed']}")
# Check target_analysed values
print(f"target_analysed: {report['target_analysed']}")
# Check events
print(f"events: {report['events']}")
# Check complete
print(f"complete: {report['complete']}")
# Check caveats
print(f"caveats: {repr(report['caveats'])}")
