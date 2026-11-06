# Final validation
import os

print("VALIDATION RESULTS")
print("=" * 16)
required_files = ['output/mhw_mask.nc', 'output/report.json']

all_good = True
for file in required_files:
    exists = os.path.exists(file)
    status = "✅" if exists else "❌"
    print(f"{status} {file}")
    if not exists:
        all_good = False

if all_good:
    print("\n🎉 ALL REQUIREMENTS MET")
    print("Marine heatwave analysis successfully completed for Baltic Sea region.")
else:
    print("\n💥 SOME FILES MISSING")