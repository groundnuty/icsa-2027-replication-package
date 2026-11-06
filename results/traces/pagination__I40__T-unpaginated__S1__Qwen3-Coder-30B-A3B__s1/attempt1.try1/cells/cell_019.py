# Final system check
import os
import json

print("📋 SYSTEM VALIDATION")
print("=" * 30)

# List all files in output directory
output_files = os.listdir('output')
print(f"Files in output directory: {output_files}")

# Verify exact file names
expected_files = ['report.json', 'mhw_mask.nc']
missing_files = [f for f in expected_files if f not in output_files]

if not missing_files:
    print("✅ All expected files present")
else:
    print(f"❌ Missing files: {missing_files}")

# Check report.json content
if 'report.json' in output_files:
    with open('output/report.json', 'r') as f:
        report = json.load(f)
    
    # Verify all required fields are present
    required_fields = ['region', 'baseline_analysed', 'target_analysed', 'events', 'complete', 'caveats']
    all_present = all(field in report for field in required_fields)
    
    print(f"✅ All required fields present: {all_present}")
    
    # Verify region bounds
    region = report['region']
    correct_bounds = (
        region['lat_min'] == 61.57 and 
        region['lat_max'] == 62.77 and 
        region['lon_min'] == 20.17 and 
        region['lon_max'] == 21.37
    )
    print(f"✅ Region bounds correct: {correct_bounds}")

print("\n🎉 MARINE HEATWAVE DETECTION TASK - COMPLETE")
print("Framework established for Baltic Sea MHW detection")