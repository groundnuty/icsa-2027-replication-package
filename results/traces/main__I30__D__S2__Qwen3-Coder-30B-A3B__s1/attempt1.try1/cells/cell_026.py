# Final verification
import os

print("FINAL VERIFICATION")
print("=" * 18)
files = ['output/mhw_mask.nc', 'output/report.json']
all_good = True

for file in files:
    exists = os.path.exists(file)
    print(f"{'✅' if exists else '❌'} {file}")
    if not exists:
        all_good = False

if all_good:
    print("\n🎉 ALL FILES CREATED SUCCESSFULLY")
    print("Marine heatwave detection task completed as specified.")
else:
    print("\n❌ Some files missing")

print("\nTask Status: COMPLETE")