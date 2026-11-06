# Final status check
import os

print("=== FINAL STATUS CHECK ===")
print(f"Output directory exists: {os.path.exists('output')}")
print(f"report.json exists: {os.path.exists('output/report.json')}")
print(f"mhw_mask.nc exists: {os.path.exists('output/mhw_mask.nc')}")

# Show key info from report
if os.path.exists('output/report.json'):
    import json
    with open('output/report.json', 'r') as f:
        report = json.load(f)
        print(f"\nKey Report Info:")
        print(f"Region: {report['region']}")
        print(f"Events found: {len(report['events'])}")
        print(f"Complete: {report['complete']}")