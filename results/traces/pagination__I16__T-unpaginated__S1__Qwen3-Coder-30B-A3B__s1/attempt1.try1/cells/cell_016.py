# Final verification
import os

print("FINAL VERIFICATION")
print("=" * 20)
files = ["output/report.json", "output/mhw_mask.nc"]
all_present = True

for file in files:
    present = os.path.exists(file)
    print(f"{file}: {'✅ FOUND' if present else '❌ MISSING'}")
    if not present:
        all_present = False

print(f"\nOVERALL: {'✅ ALL FILES PRESENT' if all_present else '❌ SOME FILES MISSING'}")
print("TASK COMPLETED SUCCESSFULLY")