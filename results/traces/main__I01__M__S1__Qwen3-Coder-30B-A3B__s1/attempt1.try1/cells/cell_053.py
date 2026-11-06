# Final confirmation
import os

print("FINAL CONFIRMATION")
print("=" * 20)
files = ["output/mhw_mask.nc", "output/report.json"]

all_created = True
for file in files:
    created = os.path.exists(file)
    print(f"{file}: {'✓' if created else '✗'}")
    if not created:
        all_created = False

print("=" * 20)
if all_created:
    print("🎉 ALL OUTPUT FILES CREATED SUCCESSFULLY")
    print("✅ TASK COMPLETED SUCCESSFULLY")
else:
    print("❌ SOME FILES MISSING")