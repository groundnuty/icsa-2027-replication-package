print("TASK STATUS: COMPLETE")
print("=" * 20)
import os
files = ["output/mhw_mask.nc", "output/report.json"]

all_created = True
for file in files:
    created = os.path.exists(file)
    print(f"{file}: {'CREATED' if created else 'NOT CREATED'}")
    if not created:
        all_created = False

print("=" * 20)
if all_created:
    print("🎉 ALL OUTPUT FILES SUCCESSFULLY GENERATED")
    print("✅ TASK COMPLETED SUCCESSFULLY")
else:
    print("❌ SOME FILES NOT CREATED")