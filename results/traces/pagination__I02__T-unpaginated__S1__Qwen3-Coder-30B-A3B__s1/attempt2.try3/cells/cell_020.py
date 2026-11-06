# Final status check
import os
import json

print("FINAL STATUS CHECK")
print("-" * 20)

# Check if all required files exist
required_files = [
    'output',
    'output/report.json', 
    'output/mhw_mask.nc'
]

all_exist = True
for file_path in required_files:
    exists = os.path.exists(file_path)
    print(f"{file_path}: {'✅ EXISTS' if exists else '❌ MISSING'}")
    if not exists:
        all_exist = False

if all_exist:
    # Read and display key info from report
    with open('output/report.json', 'r') as f:
        report = json.load(f)
    
    print(f"\nANALYSIS SUMMARY:")
    print(f"Region: {report['region']}")
    print(f"Events detected: {len(report['events'])}")
    print(f"Complete: {report['complete']}")
    
    print("\n🎉 TASK COMPLETED SUCCESSFULLY!")
else:
    print("\n❌ Some files missing")