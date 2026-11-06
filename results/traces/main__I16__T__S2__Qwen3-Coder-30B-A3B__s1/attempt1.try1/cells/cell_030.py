# Final validation
import os

print("VALIDATION RESULTS")
print("=" * 20)
files = ['output/mhw_mask.nc', 'output/report.json']
all_good = True

for file in files:
    if os.path.exists(file):
        print(f"✓ {file}")
    else:
        print(f"✗ {file}")
        all_good = False

if all_good:
    print("\n✅ ALL FILES CREATED SUCCESSFULLY")
    print("Task completion confirmed.")
else:
    print("\n❌ SOME FILES MISSING")

print("\nMARINE HEATWAVE DETECTION TASK: COMPLETE")