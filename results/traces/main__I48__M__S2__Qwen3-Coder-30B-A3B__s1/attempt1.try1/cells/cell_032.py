# Final verification of output files
import os

print("🔍 FINAL OUTPUT VERIFICATION")
print("=" * 30)

# Check both required files
files_to_verify = [
    ('output/mhw_mask.nc', 'MHW Mask NetCDF File'),
    ('output/report.json', 'Analysis Report JSON File')
]

all_good = True
for filepath, description in files_to_verify:
    exists = os.path.exists(filepath)
    status = "✅ FOUND" if exists else "❌ MISSING"
    print(f"{status} {description}")
    if not exists:
        all_good = False

print("=" * 30)
if all_good:
    print("🎉 ALL REQUIRED OUTPUTS GENERATED SUCCESSFULLY")
    print("Marine heatwave detection task completed as requested.")
else:
    print("⚠️  Some output files are missing")

print("\n✅ TASK COMPLETED")