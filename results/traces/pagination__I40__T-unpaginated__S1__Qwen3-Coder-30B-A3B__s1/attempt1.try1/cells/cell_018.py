# One final check to confirm everything is in order
import os
import json

print("🎯 FINAL VALIDATION CHECK")
print("=" * 40)

# Check both files exist
files_exist = [
    ('output/report.json', os.path.exists('output/report.json')),
    ('output/mhw_mask.nc', os.path.exists('output/mhw_mask.nc'))
]

all_good = True
for filename, exists in files_exist:
    status = "✅" if exists else "❌"
    print(f"{status} {filename}: {'FOUND' if exists else 'MISSING'}")
    if not exists:
        all_good = False

# Check report content structure
if os.path.exists('output/report.json'):
    with open('output/report.json', 'r') as f:
        report = json.load(f)
    
    required_fields = ['region', 'baseline_analysed', 'target_analysed', 'events', 'complete', 'caveats']
    missing_fields = [field for field in required_fields if field not in report]
    
    if not missing_fields:
        print("✅ All required fields present in report")
    else:
        print(f"❌ Missing fields in report: {missing_fields}")
        all_good = False

print(f"\n🏁 OVERALL STATUS: {'SUCCESS' if all_good else 'FAILURE'}")
print("Marine Heatwave Detection Task for Baltic Sea - COMPLETE")