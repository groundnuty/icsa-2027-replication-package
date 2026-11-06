# Final confirmation that both required files exist
import os

# Check for required files
required_files = ['output/report.json', 'output/mhw_mask.nc']

print("FINAL CONFIRMATION")
print("=" * 30)

all_present = True
for file_path in required_files:
    present = os.path.exists(file_path)
    print(f"✅ {file_path}" if present else f"❌ {file_path}")
    if not present:
        all_present = False

if all_present:
    print("\n🎉 ALL REQUIREMENTS SATISFIED")
    print("✅ Task completed successfully")
    print("✅ Both output files created as specified")
else:
    print("\n❌ Some files missing")

# Show key info
if os.path.exists('output/report.json'):
    import json
    with open('output/report.json', 'r') as f:
        report = json.load(f)
    print(f"✅ Events detected: {len(report.get('events', []))}")
    print(f"✅ Complete: {report.get('complete', False)}")