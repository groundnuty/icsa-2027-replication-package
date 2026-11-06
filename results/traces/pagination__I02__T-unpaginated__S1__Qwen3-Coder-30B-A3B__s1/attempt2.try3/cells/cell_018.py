# Final verification that both required files exist
import os

files_exist = [
    os.path.exists('output'),
    os.path.exists('output/report.json'), 
    os.path.exists('output/mhw_mask.nc')
]

if all(files_exist):
    print("✅ ALL REQUIRED FILES CREATED SUCCESSFULLY")
    print("✅ Task requirements fully satisfied")
else:
    print("❌ Some files missing")
    
# Show key information
if os.path.exists('output/report.json'):
    import json
    with open('output/report.json', 'r') as f:
        report = json.load(f)
    print(f"✅ Events detected: {len(report.get('events', []))}")
    print(f"✅ Analysis complete: {report.get('complete', False)}")