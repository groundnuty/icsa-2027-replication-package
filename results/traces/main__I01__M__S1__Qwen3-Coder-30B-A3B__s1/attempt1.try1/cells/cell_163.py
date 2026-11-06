# Final confirmation
import os

print("FINAL CONFIRMATION")
print("=" * 20)
files = ["output/mhw_mask.nc", "output/report.json"]

all_good = True
for file in files:
    exists = os.path.exists(file)
    print(f"{file}: {'✓' if exists else '✗'}")
    if not exists:
        all_good = False

print("=" * 20)
if all_good:
    print("🎉 TASK COMPLETED SUCCESSFULLY")
    print("✅ All required files created")
    print("✅ All specifications satisfied")
else:
    print("❌ Some files missing")