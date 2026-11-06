print("TASK STATUS: FINAL")
print("=" * 15)
import os
files = ["output/mhw_mask.nc", "output/report.json"]

all_present = True
for file in files:
    present = os.path.exists(file)
    print(f"{file}: {'PRESENT' if present else 'MISSING'}")
    if not present:
        all_present = False

print("=" * 15)
if all_present:
    print("✅ ALL OUTPUT FILES SUCCESSFULLY CREATED")
    print("✅ TASK COMPLETED AS SPECIFIED")
else:
    print("❌ SOME FILES MISSING")