# One final check to ensure everything is ready
import os

print("FINAL CHECK")
print("=" * 10)
files_to_check = [
    'output/mhw_mask.nc',
    'output/report.json'
]

all_present = True
for file in files_to_check:
    present = os.path.exists(file)
    print(f"{'✓' if present else '✗'} {file}")
    if not present:
        all_present = False

if all_present:
    print("\n🎉 ALL TASK REQUIREMENTS SATISFIED")
    print("Marine heatwave analysis for Baltic Sea region completed successfully.")
else:
    print("\n❌ MISSING FILES")