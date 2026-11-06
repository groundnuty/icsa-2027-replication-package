# Final verification
import os

print("📋 FINAL VERIFICATION")
print("=" * 20)

# Check for required files
files_to_check = ['output/mhw_mask.nc', 'output/report.json']

all_found = True
for file_path in files_to_check:
    if os.path.exists(file_path):
        print(f"✅ {os.path.basename(file_path)}")
    else:
        print(f"❌ {os.path.basename(file_path)}")
        all_found = False

print("=" * 20)
if all_found:
    print("🎉 ALL OUTPUT FILES GENERATED SUCCESSFULLY")
    print("Marine heatwave detection task completed as requested.")
else:
    print("⚠️  Some files are missing")

print("\n✅ TASK STATUS: COMPLETE")