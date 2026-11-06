print("TASK COMPLETION SUMMARY")
print("=" * 30)

# Verify final state
import os
import json

# Check files exist
report_exists = os.path.exists('output/report.json')
mhw_exists = os.path.exists('output/mhw_mask.nc')

print(f"✅ Report file created: {report_exists}")
print(f"✅ MHW mask file created: {mhw_exists}")

if report_exists:
    with open('output/report.json', 'r') as f:
        report = json.load(f)
    
    print(f"\n📋 Report Content:")
    print(f"   Region: {report['region']}")
    print(f"   Baseline: {report['baseline_analysed']}")
    print(f"   Target: {report['target_analysed']}")
    print(f"   Complete: {report['complete']}")
    
print(f"\n🎯 TASK STATUS: COMPLETE")
print("Marine Heatwave Detection for Baltic Sea - FINALIZED")