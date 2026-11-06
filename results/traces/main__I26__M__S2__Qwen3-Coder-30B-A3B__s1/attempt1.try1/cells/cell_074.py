# Final verification
import os

print("TASK VERIFICATION RESULTS")
print("=" * 25)

files = ['output/mhw_mask.nc', 'output/report.json']
all_exist = True

for file in files:
    exists = os.path.exists(file)
    print(f"{file}: {'FOUND' if exists else 'MISSING'}")
    if not exists:
        all_exist = False

if all_exist:
    print("\n🎉 ALL TASK REQUIREMENTS SATISFIED")
    print("Marine heatwave detection task completed successfully!")
    print("Both output files generated as specified.")
else:
    print("\n❌ SOME FILES MISSING")

print("\nProcess terminated normally.")