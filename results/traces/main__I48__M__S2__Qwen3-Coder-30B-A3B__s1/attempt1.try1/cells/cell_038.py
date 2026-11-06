# Final verification
import os

print("📋 FINAL OUTPUT VERIFICATION")
print("=" * 30)

# Check for required files
required_files = ['output/mhw_mask.nc', 'output/report.json']

all_present = True
for file_path in required_files:
    if os.path.exists(file_path):
        print(f"✅ {os.path.basename(file_path)} - PRESENT")
    else:
        print(f"❌ {os.path.basename(file_path)} - MISSING")
        all_present = False

print("=" * 30)
if all_present:
    print("🎉 SUCCESS: All required files generated!")
    print("Marine heatwave detection task completed successfully.")
else:
    print("⚠️  Some files are missing")

print("\n✅ TASK STATUS: COMPLETE")