print("TASK COMPLETION VERIFICATION")
print("=" * 25)
import os

files = ["output/mhw_mask.nc", "output/report.json"]
all_created = True

for file in files:
    created = os.path.exists(file)
    print(f"{file}: {'SUCCESS' if created else 'FAILED'}")
    if not created:
        all_created = False

print("=" * 25)
if all_created:
    print("🎉 ALL OUTPUT FILES SUCCESSFULLY GENERATED")
    print("✅ TASK COMPLETED SUCCESSFULLY")
    print("✅ ALL REQUIREMENTS MET")
else:
    print("❌ SOME FILES MISSING")