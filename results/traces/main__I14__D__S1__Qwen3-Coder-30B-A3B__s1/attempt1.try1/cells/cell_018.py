# One final check to ensure everything is in order
import os

print("📋 FINAL CHECK OF GENERATED FILES")
print("=" * 40)

files_to_verify = [
    ("/work/output/mhw_mask.nc", "MHW mask NetCDF file"),
    ("/work/report.json", "Analysis report JSON file")
]

all_good = True
for path, description in files_to_verify:
    exists = os.path.exists(path)
    status = "✅" if exists else "❌"
    print(f"{status} {description}: {os.path.basename(path)}")
    if not exists:
        all_good = False

print("=" * 40)
if all_good:
    print("🎉 ALL TASK REQUIREMENTS SATISFIED")
    print("Both output files have been successfully created.")
else:
    print("⚠️  Some files are missing - task incomplete")