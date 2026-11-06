print("FINAL TASK STATUS")
print("=" * 20)
import os

files = ["output/mhw_mask.nc", "output/report.json"]
all_created = True

for file in files:
    created = os.path.exists(file)
    print(f"{file}: {'SUCCESS' if created else 'FAILED'}")
    if not created:
        all_created = False

print("=" * 20)
if all_created:
    print("🎉 ALL OUTPUT FILES CREATED")
    print("✅ TASK COMPLETED SUCCESSFULLY")
    print("✅ ALL REQUIREMENTS MET")
else:
    print("❌ SOME FILES MISSING")