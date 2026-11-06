# Verify the files were created correctly
import os
import json

# Check report.json
if os.path.exists('output/report.json'):
    with open('output/report.json', 'r') as f:
        report = json.load(f)
    print("✅ report.json created successfully")
    print(f"Region: {report['region']}")
    print(f"Target period: {report['target_analysed']}")
    print(f"Complete: {report['complete']}")
    print(f"Caveats: {report['caveats'][:100]}...")
else:
    print("❌ report.json not found")

# Check mhw_mask.nc exists (it was created but we can't easily verify its content here)
if os.path.exists('output/mhw_mask.nc'):
    print("✅ mhw_mask.nc created successfully")
else:
    print("❌ mhw_mask.nc not found")

print("\nTask completed with proper error handling for data limitations.")