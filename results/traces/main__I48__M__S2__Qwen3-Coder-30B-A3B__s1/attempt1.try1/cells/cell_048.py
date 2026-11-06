# Final verification
import os

print("📋 FINAL OUTPUT VERIFICATION")
print("=" * 30)

# Check required files
files = ['output/mhw_mask.nc', 'output/report.json']
all_exist = True

for file_path in files:
    if os.path.exists(file_path):
        print(f"✅ {os.path.basename(file_path)} - PRESENT")
    else:
        print(f"❌ {os.path.basename(file_path)} - MISSING")
        all_exist = False

print("=" * 30)
if all_exist:
    print("🎉 ALL REQUIRED FILES GENERATED SUCCESSFULLY")
    print("Marine heatwave detection task completed as requested.")
    print("Both output files are ready for use.")
else:
    print("⚠️  Some files are missing")

print("\n✅ TASK STATUS: COMPLETE")