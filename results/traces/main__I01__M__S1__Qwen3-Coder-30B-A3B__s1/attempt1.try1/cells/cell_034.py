# Final confirmation that both files exist
import os

print("FINAL CONFIRMATION")
print("=" * 15)
files = ["output/mhw_mask.nc", "output/report.json"]

all_exist = True
for file in files:
    exists = os.path.exists(file)
    print(f"{file}: {'FOUND' if exists else 'MISSING'}")
    if not exists:
        all_exist = False

print("=" * 15)
if all_exist:
    print("✅ ALL OUTPUT FILES CREATED SUCCESSFULLY")
    print("✅ TASK COMPLETED SUCCESSFULLY")
else:
    print("❌ SOME FILES MISSING")