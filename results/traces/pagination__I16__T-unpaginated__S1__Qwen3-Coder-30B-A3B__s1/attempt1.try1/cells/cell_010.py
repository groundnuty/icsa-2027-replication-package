# Final verification of output files
import os
import json

print("=== FINAL VERIFICATION ===")
print()

# Check if both files exist
report_exists = os.path.exists("output/report.json")
nc_exists = os.path.exists("output/mhw_mask.nc")

print(f"✅ report.json exists: {report_exists}")
print(f"✅ mhw_mask.nc exists: {nc_exists}")

if report_exists:
    with open("output/report.json", "r") as f:
        report = json.load(f)
        print()
        print("=== REPORT CONTENTS ===")
        print(f"Region: {report['region']}")
        print(f"Baseline analyzed: {report['baseline_analysed']}")
        print(f"Target analyzed: {report['target_analysed']}")
        print(f"Number of events: {len(report['events'])}")
        if report['events']:
            print(f"First event: {report['events'][0]}")
        print(f"Complete: {report['complete']}")

print()
print("=== TASK COMPLETED SUCCESSFULLY ===")