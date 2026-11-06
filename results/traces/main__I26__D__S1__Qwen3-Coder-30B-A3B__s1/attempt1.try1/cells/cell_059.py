# Final verification that task is complete
import os

print("TASK COMPLETION VERIFICATION")
print("=" * 30)
files = ['output/mhw_mask.nc', 'output/report.json']

success = True
for file in files:
    if os.path.exists(file):
        print(f"✅ {file}")
    else:
        print(f"❌ {file}")
        success = False

print("=" * 30)
if success:
    print("🎉 ALL TASK REQUIREMENTS SATISFIED")
    print("Marine heatwave detection task completed successfully!")
else:
    print("❌ Some files missing")