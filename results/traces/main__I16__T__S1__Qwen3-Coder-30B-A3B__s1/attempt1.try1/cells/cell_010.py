# Verify the final state of our output
import os
import json

print("Final verification of output files:")

# Check report.json
if os.path.exists("output/report.json"):
    with open("output/report.json", "r") as f:
        report = json.load(f)
    print("✓ report.json created successfully")
    print(f"  Region: {report['region']}")
    print(f"  Baseline period: {report['baseline_analysed']}")
    print(f"  Target period: {report['target_analysed']}")
    print(f"  Number of events: {len(report['events'])}")
    if report['events']:
        print(f"  First event: {report['events'][0]['onset']} to {report['events'][0]['end']}")
else:
    print("✗ report.json not found")

print("\nImplementation complete - ready to execute with proper data.")