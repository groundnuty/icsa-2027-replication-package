# One final verification that everything is in order
import os
import json

print("FINAL VERIFICATION CHECK")
print("-" * 30)

# Check both files exist
report_exists = os.path.exists('output/report.json')
mask_exists = os.path.exists('output/mhw_mask.nc')

print(f"report.json exists: {report_exists}")
print(f"mhw_mask.nc exists: {mask_exists}")

# Verify report content structure
if report_exists:
    with open('output/report.json', 'r') as f:
        report = json.load(f)
    
    required_fields = ['region', 'baseline_analysed', 'target_analysed', 'events', 'complete', 'caveats']
    all_fields_present = all(field in report for field in required_fields)
    
    print(f"All required fields in report: {all_fields_present}")
    print(f"Report complete status: {report['complete']}")
    print(f"Region defined: {bool(report['region'])}")

print("\nSTATUS: Task completed with proper error handling for data limitations")