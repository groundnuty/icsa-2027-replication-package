# Final status check
import os

print("FINAL STATUS")
print("=" * 12)
files = ["output/mhw_mask.nc", "output/report.json"]
all_created = True

for file in files:
    status = "CREATED" if os.path.exists(file) else "MISSING"
    print(f"{file}: {status}")
    if not os.path.exists(file):
        all_created = False

print("=" * 12)
if all_created:
    print("✅ TASK COMPLETED SUCCESSFULLY")
else:
    print("❌ SOME FILES MISSING")