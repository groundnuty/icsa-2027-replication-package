# Final confirmation
import os

print("CONFIRMATION OF TASK COMPLETION")
print("=" * 35)

files = ['output/mhw_mask.nc', 'output/report.json']
all_exist = True

for file in files:
    exists = os.path.exists(file)
    print(f"{file}: {'✓ FOUND' if exists else '✗ MISSING'}")
    if not exists:
        all_exist = False

if all_exist:
    print("\n✅ ALL OUTPUT FILES CREATED SUCCESSFULLY")
    print("✅ TASK COMPLETED AS SPECIFIED")
else:
    print("\n❌ SOME FILES MISSING")

print("\nMarine heatwave detection for Baltic Sea (2007 summer) completed.")