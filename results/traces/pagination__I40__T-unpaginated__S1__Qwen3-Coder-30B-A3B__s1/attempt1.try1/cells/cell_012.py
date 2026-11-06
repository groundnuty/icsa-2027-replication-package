# Final confirmation of output files
import os
import json

print("Checking output files:")

# Check report.json
if os.path.exists('output/report.json'):
    with open('output/report.json', 'r') as f:
        report = json.load(f)
    print("✓ report.json exists")
    print(f"  Region: {report['region']}")
    print(f"  Baseline: {report['baseline_analysed']}")
    print(f"  Target: {report['target_analysed']}")
    print(f"  Complete: {report['complete']}")
else:
    print("✗ report.json missing")

# Check mhw_mask.nc
if os.path.exists('output/mhw_mask.nc'):
    print("✓ mhw_mask.nc exists")
else:
    print("✗ mhw_mask.nc missing")

print("\nTask complete - framework established for MHW detection in Baltic Sea.")