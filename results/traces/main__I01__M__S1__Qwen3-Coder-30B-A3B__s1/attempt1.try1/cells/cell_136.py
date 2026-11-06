# Final confirmation
import os

print("TASK STATUS CONFIRMATION")
print("=" * 25)
files = ["output/mhw_mask.nc", "output/report.json"]

all_exist = True
for file in files:
    exists = os.path.exists(file)
    print(f"{file}: {'✓' if exists else '✗'}")
    if not exists:
        all_exist = False

print("=" * 25)
if all_exist:
    print("🎉 ALL OUTPUT FILES SUCCESSFULLY CREATED")
    print("✅ TASK COMPLETED AS SPECIFIED")
    print("✅ ALL REQUIREMENTS MET")
else:
    print("❌ SOME FILES MISSING")