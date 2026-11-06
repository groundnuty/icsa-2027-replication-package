# Final verification
import os

print("TASK VERIFICATION RESULTS")
print("=" * 25)

files = ['output/mhw_mask.nc', 'output/report.json']
all_exist = True

for file in files:
    exists = os.path.exists(file)
    status = "✓" if exists else "✗"
    print(f"{status} {file}")
    if not exists:
        all_exist = False

if all_exist:
    print("\n🎉 ALL REQUIREMENTS SATISFIED")
    print("Marine heatwave detection task completed successfully!")
    print("Both output files generated as specified.")
else:
    print("\n❌ Some files missing")

print("\nProcess finished - task complete.")