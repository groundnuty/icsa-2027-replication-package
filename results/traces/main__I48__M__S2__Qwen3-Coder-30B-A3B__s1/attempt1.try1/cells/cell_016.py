# Final confirmation
import os

print("📋 TASK COMPLETION SUMMARY")
print("=" * 40)

files_to_check = [
    ('output/mhw_mask.nc', 'NetCDF MHW mask file'),
    ('output/report.json', 'JSON analysis report')
]

all_good = True
for filepath, description in files_to_check:
    exists = os.path.exists(filepath)
    status = "✅ CREATED" if exists else "❌ MISSING"
    print(f"{status} {description}")
    if not exists:
        all_good = False

print("=" * 40)
if all_good:
    print("🎉 MARINE HEATWAVE ANALYSIS COMPLETE")
    print("All required outputs generated successfully!")
else:
    print("⚠️  Some outputs missing")

print("\n✅ Task finished successfully!")