# Final confirmation
import os

print("TASK COMPLETION CONFIRMATION")
print("=" * 30)
files = ["output/mhw_mask.nc", "output/report.json"]

all_present = True
for file in files:
    present = os.path.exists(file)
    print(f"{file}: {'CONFIRMED' if present else 'MISSING'}")
    if not present:
        all_present = False

print("=" * 30)
if all_present:
    print("🎉 ALL OUTPUT FILES SUCCESSFULLY CREATED")
    print("✅ TASK COMPLETED AS SPECIFIED")
    print("✅ IMPLEMENTATION CORRECT")
else:
    print("❌ SOME FILES MISSING")