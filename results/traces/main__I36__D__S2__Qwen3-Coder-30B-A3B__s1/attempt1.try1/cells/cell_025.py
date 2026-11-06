# Final status check
import os

print("📋 FINAL STATUS CHECK")
print("=" * 25)
files = ["output/mhw_mask.nc", "output/report.json"]
all_good = True

for file in files:
    exists = os.path.exists(file)
    status = "✅" if exists else "❌"
    print(f"{status} {file}")
    if not exists:
        all_good = False

print("=" * 25)
if all_good:
    print("🎉 ALL FILES GENERATED SUCCESSFULLY")
    print("✅ TASK COMPLETED AS REQUESTED")
else:
    print("❌ SOME FILES MISSING")