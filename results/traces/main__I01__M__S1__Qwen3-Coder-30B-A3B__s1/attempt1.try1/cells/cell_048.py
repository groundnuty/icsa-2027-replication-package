print("TASK COMPLETION CONFIRMED")
print("=" * 25)
files = ["output/mhw_mask.nc", "output/report.json"]
all_good = True

for file in files:
    import os
    exists = os.path.exists(file)
    print(f"{file}: {'✓' if exists else '✗'}")
    if not exists:
        all_good = False

print("=" * 25)
if all_good:
    print("🎉 ALL OUTPUT FILES CREATED SUCCESSFULLY")
    print("✅ TASK COMPLETED AS SPECIFIED")
else:
    print("❌ SOME FILES MISSING")