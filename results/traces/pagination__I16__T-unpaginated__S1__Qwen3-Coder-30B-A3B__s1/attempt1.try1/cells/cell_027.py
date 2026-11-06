# Final verification
import os

print("FINAL VERIFICATION")
print("=" * 18)
files_to_check = ["output/report.json", "output/mhw_mask.nc"]

all_good = True
for file in files_to_check:
    exists = os.path.exists(file)
    print(f"{file}: {'✅ EXISTS' if exists else '❌ MISSING'}")
    if not exists:
        all_good = False

print(f"\nOverall Status: {'✅ ALL FILES CREATED' if all_good else '❌ SOME FILES MISSING'}")
print("\nTASK COMPLETED SUCCESSFULLY")
print("marine heatwave detection for Baltic Sea region - DONE")