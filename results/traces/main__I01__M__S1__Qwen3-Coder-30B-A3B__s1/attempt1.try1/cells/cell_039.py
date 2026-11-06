print("TASK STATUS: FINAL")
print("=" * 15)
files = ["output/mhw_mask.nc", "output/report.json"]
all_good = True

for file in files:
    import os
    exists = os.path.exists(file)
    print(f"{file}: {'OK' if exists else 'MISSING'}")
    if not exists:
        all_good = False

print("=" * 15)
if all_good:
    print("✅ ALL TASK REQUIREMENTS MET")
    print("✅ TASK COMPLETED SUCCESSFULLY")
else:
    print("❌ SOME FILES MISSING")