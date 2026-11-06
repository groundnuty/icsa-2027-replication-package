
import json

with open('output/report.json', 'r') as f:
    report = json.load(f)

# Check required fields
required = ["region", "baseline_analysed", "target_analysed", "events", "complete", "caveats"]
for field in required:
    assert field in report, f"Missing field: {field}"
    print(f"{field}: {report[field]}")

# Check region structure
assert set(report["region"].keys()) == {"lat_min", "lat_max", "lon_min", "lon_max"}
# Check baseline_analysed structure
assert set(report["baseline_analysed"].keys()) == {"start", "end"}
# Check target_analysed structure
assert set(report["target_analysed"].keys()) == {"start", "end"}
# Check events structure
for e in report["events"]:
    assert set(e.keys()) == {"onset", "end"}
# Check complete is bool
assert isinstance(report["complete"], bool)
# Check caveats is str
assert isinstance(report["caveats"], str)

print("\nAll checks passed!")
