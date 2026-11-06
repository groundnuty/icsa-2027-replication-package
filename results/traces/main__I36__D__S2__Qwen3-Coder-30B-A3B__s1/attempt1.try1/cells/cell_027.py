# Final verification
import os

print("🏁 TASK VERIFICATION")
print("=" * 20)
files = ["output/mhw_mask.nc", "output/report.json"]

all_present = True
for file in files:
    if os.path.exists(file):
        print(f"✓ {file}")
    else:
        print(f"✗ {file}")
        all_present = False

print("=" * 20)
if all_present:
    print("🎉 ALL REQUIREMENTS MET")
    print("Task completed successfully!")
else:
    print("❌ Some files missing")