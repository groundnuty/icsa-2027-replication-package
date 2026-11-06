# Final confirmation that both files exist
import os

files = ['output/mhw_mask.nc', 'output/report.json']
all_exist = True

for file in files:
    if not os.path.exists(file):
        print(f"MISSING: {file}")
        all_exist = False
    else:
        print(f"FOUND: {file}")

if all_exist:
    print("\n🎉 ALL OUTPUT FILES GENERATED SUCCESSFULLY")
    print("Task execution completed successfully!")
else:
    print("\n❌ SOME FILES MISSING")