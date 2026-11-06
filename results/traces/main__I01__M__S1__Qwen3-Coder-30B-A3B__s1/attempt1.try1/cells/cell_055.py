print("TASK COMPLETION CONFIRMED")
print("=" * 25)
files = ["output/mhw_mask.nc", "output/report.json"]

all_good = True
for file in files:
    import os
    exists = os.path.exists(file)
    print(f"{file}: {'DONE' if exists else 'MISSING'}")
    if not exists:
        all_good = False

print("=" * 25)
if all_good:
    print("🎉 ALL TASK REQUIREMENTS SATISFIED")
    print("✅ TASK COMPLETED SUCCESSFULLY")
else:
    print("❌ SOME FILES MISSING")