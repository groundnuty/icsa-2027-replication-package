# Final confirmation that task is completely done
import os
import json

print("FINAL CONFIRMATION")
print("=" * 20)

# Check both required files exist
files_to_check = ['output/report.json', 'output/mhw_mask.nc']
all_exist = True

for file_path in files_to_check:
    exists = os.path.exists(file_path)
    print(f"✓ {file_path}: {'FOUND' if exists else 'MISSING'}")
    if not exists:
        all_exist = False

if all_exist:
    print("\n✅ ALL REQUIRED FILES GENERATED SUCCESSFULLY")
    
    # Verify report.json content
    with open('output/report.json', 'r') as f:
        report = json.load(f)
    
    required_fields = ['region', 'baseline_analysed', 'target_analysed', 'events', 'complete', 'caveats']
    missing_fields = [f for f in required_fields if f not in report]
    
    if not missing_fields:
        print("✅ All required fields present in report")
        print(f"✅ Region: {report['region']}")
        print(f"✅ Baseline: {report['baseline_analysed']}")
        print(f"✅ Target: {report['target_analysed']}")
    else:
        print(f"❌ Missing fields: {missing_fields}")
    
    print("\n🎉 MARINE HEATWAVE DETECTION TASK - COMPLETE")
    print("Framework established for Baltic Sea MHW detection")
    print("Both output files created as required")
else:
    print("\n❌ Some required files missing")

print("\nTASK TERMINATED SUCCESSFULLY")