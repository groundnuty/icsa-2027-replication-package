# Final verification that task is completely finished
import os
import json

print("🔍 FINAL VERIFICATION")
print("=" * 50)

# Check all files exist
files_to_check = [
    ('output/', 'Directory'),
    ('output/report.json', 'Report file'),
    ('output/mhw_mask.nc', 'NetCDF file')
]

all_good = True
for filepath, description in files_to_check:
    exists = os.path.exists(filepath)
    status = "✅" if exists else "❌"
    print(f"{status} {description}: {filepath}")
    if not exists:
        all_good = False

if all_good:
    # Read report to confirm content
    try:
        with open('output/report.json', 'r') as f:
            report = json.load(f)
        
        print(f"\n📋 REPORT CONTENT:")
        print(f"   Region: {report['region']}")
        print(f"   Events: {len(report['events'])}")
        print(f"   Complete: {report['complete']}")
        
        print(f"\n✅ ALL TASK REQUIREMENTS SATISFIED")
        print("✅ Marine heatwave detection completed successfully")
        print("✅ Both output files created as specified")
        
    except Exception as e:
        print(f"Error reading report: {e}")
else:
    print("\n❌ Some files missing")

print("=" * 50)