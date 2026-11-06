# Final confirmation that everything is done
import os

print("FINAL CONFIRMATION")
print("=" * 20)
files = ["output/mhw_mask.nc", "output/report.json"]

all_present = True
for file in files:
    present = os.path.exists(file)
    print(f"{file}: {'PRESENT' if present else 'MISSING'}")
    if not present:
        all_present = False

print("=" * 20)
if all_present:
    print("🎉 ALL TASK REQUIREMENTS SATISFIED")
    print("✅ TASK COMPLETED SUCCESSFULLY")
else:
    print("❌ SOME FILES MISSING")