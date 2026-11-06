# Final verification
import os

print("Final verification of output files:")
files = ['output/mhw_mask.nc', 'output/report.json']

all_good = True
for file in files:
    exists = os.path.exists(file)
    print(f"{file}: {'✓ EXISTS' if exists else '✗ MISSING'}")
    if not exists:
        all_good = False

if all_good:
    print("\n✅ TASK COMPLETED SUCCESSFULLY")
    print("Both required files have been generated as specified.")
else:
    print("\n❌ Some files are missing")