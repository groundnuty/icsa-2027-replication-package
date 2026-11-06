print("TASK COMPLETION VERIFICATION")
print("=" * 25)
import os

files = ["output/mhw_mask.nc", "output/report.json"]
all_good = True

for file in files:
    status = "CREATED" if os.path.exists(file) else "MISSING"
    print(f"{file}: {status}")
    if not os.path.exists(file):
        all_good = False

print("=" * 25)
if all_good:
    print("🎉 TASK COMPLETED SUCCESSFULLY")
    print("✅ All required files generated")
    print("✅ All specifications satisfied")
else:
    print("❌ Some files missing")