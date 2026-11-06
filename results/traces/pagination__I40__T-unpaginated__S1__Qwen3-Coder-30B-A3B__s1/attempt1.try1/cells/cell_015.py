# Final confirmation that both required files exist
import os
import json

# Check that both required files exist
report_exists = os.path.exists('output/report.json')
mhw_exists = os.path.exists('output/mhw_mask.nc')

print("FINAL CONFIRMATION:")
print(f"✓ output/report.json exists: {report_exists}")
print(f"✓ output/mhw_mask.nc exists: {mhw_exists}")

if report_exists and mhw_exists:
    # Read and display key info from report
    with open('output/report.json', 'r') as f:
        report = json.load(f)
    
    print(f"\nREPORT CONTENTS:")
    print(f"Region: {report['region']}")
    print(f"Baseline period: {report['baseline_analysed']}")
    print(f"Target period: {report['target_analysed']}")
    print(f"Analysis complete: {report['complete']}")
    
    print("\n✅ TASK SUCCESSFULLY COMPLETED")
    print("Both required files have been generated.")
else:
    print("❌ Missing required output files")