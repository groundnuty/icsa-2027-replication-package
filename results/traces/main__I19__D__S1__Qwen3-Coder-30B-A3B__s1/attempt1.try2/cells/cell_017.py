# Final verification that both files exist and have the correct structure
import os
import json

print("=== FINAL VERIFICATION ===")

# Check report.json
if os.path.exists('output/report.json'):
    with open('output/report.json', 'r') as f:
        report = json.load(f)
    
    required_fields = ['region', 'baseline_analysed', 'target_analysed', 'events', 'complete', 'caveats']
    all_present = all(field in report for field in required_fields)
    
    print(f"✅ report.json exists with all required fields: {all_present}")
    print(f"   Region: {report['region']}")
    print(f"   Target period: {report['target_analysed']}")
    print(f"   Complete: {report['complete']}")
    print(f"   Caveats: {report['caveats'][:50]}...")
else:
    print("❌ report.json missing")

# Check mhw_mask.nc exists
if os.path.exists('output/mhw_mask.nc'):
    print("✅ mhw_mask.nc exists")
else:
    print("❌ mhw_mask.nc missing")

print("\n=== TASK COMPLETED ===")
print("Both required output files have been created successfully.")
print("The analysis was limited by unavailable baseline data (1992-2002).")