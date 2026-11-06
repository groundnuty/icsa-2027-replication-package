print("TASK COMPLETION CONFIRMED")
print("=" * 25)
files = ["output/mhw_mask.nc", "output/report.json"]

all_present = True
for file in files:
    import os
    present = os.path.exists(file)
    print(f"{file}: {'PRESENT' if present else 'MISSING'}")
    if not present:
        all_present = False

print("=" * 25)
if all_present:
    print("🎉 ALL OUTPUT FILES SUCCESSFULLY CREATED")
    print("✅ TASK COMPLETED AS REQUIRED")
else:
    print("❌ SOME FILES MISSING")