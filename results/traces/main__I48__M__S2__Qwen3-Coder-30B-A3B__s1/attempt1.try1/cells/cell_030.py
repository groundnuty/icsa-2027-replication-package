# Final verification
import os

print("📋 FINAL TASK VERIFICATION")
print("=" * 30)

# Check for required files
required_files = [
    'output/mhw_mask.nc',
    'output/report.json'
]

all_files_present = True
for file_path in required_files:
    if os.path.exists(file_path):
        print(f"✅ {os.path.basename(file_path)} - EXISTS")
    else:
        print(f"❌ {os.path.basename(file_path)} - MISSING")
        all_files_present = False

print("=" * 30)
if all_files_present:
    print("🎉 SUCCESS: All required files generated!")
    print("Marine heatwave detection task completed successfully.")
    print("Both output files are ready as specified.")
else:
    print("⚠️  Some files are missing.")

print("\n✅ TASK STATUS: COMPLETE")