print("FINAL VERIFICATION")
print("=" * 18)
import os

files = ["output/report.json", "output/mhw_mask.nc"]
all_exist = True

for file in files:
    exists = os.path.exists(file)
    print(f"{'✅' if exists else '❌'} {file}")
    if not exists:
        all_exist = False

print(f"\nOverall: {'SUCCESS' if all_exist else 'FAILURE'}")
print("\nMARINE HEATWAVE DETECTION TASK - COMPLETE")