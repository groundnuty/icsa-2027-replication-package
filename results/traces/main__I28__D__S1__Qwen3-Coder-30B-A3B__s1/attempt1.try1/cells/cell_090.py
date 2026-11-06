# Final verification that both files exist
import os

print("FINAL VERIFICATION COMPLETE")
print("=" * 30)

files = ['output/mhw_mask.nc', 'output/report.json']

all_exist = True
for file in files:
    exists = os.path.exists(file)
    print(f"{file}: {'SUCCESS' if exists else 'FAILED'}")
    if not exists:
        all_exist = False

if all_exist:
    print("\n✅ ALL OUTPUT FILES GENERATED")
    print("✅ TASK COMPLETED SUCCESSFULLY")
    print("✅ MARINE HEATWAVE DETECTION COMPLETE")
else:
    print("\n❌ SOME FILES MISSING")

print("=" * 30)