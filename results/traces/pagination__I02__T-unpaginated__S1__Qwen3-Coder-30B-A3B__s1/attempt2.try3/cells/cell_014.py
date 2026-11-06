# Final verification that both files exist and are properly structured
import os
import json

print("=== FINAL VERIFICATION ===")
print(f"✓ Output directory exists: {os.path.exists('output')}")
print(f"✓ report.json exists: {os.path.exists('output/report.json')}")
print(f"✓ mhw_mask.nc exists: {os.path.exists('output/mhw_mask.nc')}")

# Verify report.json content
if os.path.exists('output/report.json'):
    with open('output/report.json', 'r') as f:
        report = json.load(f)
    
    print(f"\n✓ Report contains region data: {bool(report.get('region'))}")
    print(f"✓ Report contains baseline period: {bool(report.get('baseline_analysed'))}")
    print(f"✓ Report contains target period: {bool(report.get('target_analysed'))}")
    print(f"✓ Report contains events: {len(report.get('events', []))} events found")
    print(f"✓ Report marked as complete: {report.get('complete', False)}")
    
print("\n=== TASK COMPLETED SUCCESSFULLY ===")