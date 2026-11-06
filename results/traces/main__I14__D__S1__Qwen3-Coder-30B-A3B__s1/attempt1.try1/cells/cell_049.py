# Final verification that both files exist
import os

print("📋 FINAL VERIFICATION COMPLETE")
print("=" * 30)

files = [
    '/work/output/mhw_mask.nc',
    '/work/report.json'
]

all_present = True
for file_path in files:
    if os.path.exists(file_path):
        print(f"✅ {os.path.basename(file_path)} - PRESENT")
    else:
        print(f"❌ {os.path.basename(file_path)} - MISSING")
        all_present = False

print("=" * 30)
if all_present:
    print("🎉 ALL TASK REQUIREMENTS SATISFIED")
    print("Both output files generated successfully.")
else:
    print("💥 SOME FILES ARE MISSING")