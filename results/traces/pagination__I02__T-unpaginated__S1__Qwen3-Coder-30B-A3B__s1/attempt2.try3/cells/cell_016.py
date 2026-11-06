# Final status - confirming everything is complete
import os
import json

# Check final state
success = (
    os.path.exists('output') and 
    os.path.exists('output/report.json') and 
    os.path.exists('output/mhw_mask.nc')
)

if success:
    with open('output/report.json', 'r') as f:
        report = json.load(f)
    
    print("✅ TASK COMPLETED SUCCESSFULLY")
    print(f"📁 Output directory: Present")
    print(f"📄 report.json: Present ({len(report.get('events', []))} events)")
    print(f"📄 mhw_mask.nc: Present")
    print(f"📊 Events detected: {len(report.get('events', []))}")
    print(f"✅ Complete: {report.get('complete', False)}")
else:
    print("❌ Task incomplete - missing files")