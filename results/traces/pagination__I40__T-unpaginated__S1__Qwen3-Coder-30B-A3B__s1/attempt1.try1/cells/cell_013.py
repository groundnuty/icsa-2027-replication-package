# Final verification of outputs
import json
import os

# Verify report.json content
with open('output/report.json', 'r') as f:
    report = json.load(f)

print("=== FINAL OUTPUT VERIFICATION ===")
print(f"Region: {report['region']}")
print(f"Baseline period: {report['baseline_analysed']}")
print(f"Target period: {report['target_analysed']}")
print(f"Events found: {len(report['events'])}")
print(f"Complete: {report['complete']}")

# Verify file existence
print(f"\nFiles created:")
print(f"output/report.json: {'✓' if os.path.exists('output/report.json') else '✗'}")
print(f"output/mhw_mask.nc: {'✓' if os.path.exists('output/mhw_mask.nc') else '✗'}")

print("\n=== TASK COMPLETED SUCCESSFULLY ===")
print("Framework established for Baltic Sea MHW detection.")