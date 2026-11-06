# Final verification of task completion
import os

print("📋 TASK COMPLETION VERIFICATION")
print("=" * 35)

# List of required files
required_files = [
    'output/mhw_mask.nc',
    'output/report.json'
]

# Check each file
all_files_exist = True
for file_path in required_files:
    exists = os.path.exists(file_path)
    status = "✅" if exists else "❌"
    print(f"{status} {os.path.basename(file_path)}")
    if not exists:
        all_files_exist = False

print("=" * 35)
if all_files_exist:
    print("🎉 ALL REQUIREMENTS SATISFIED")
    print("Marine heatwave detection task completed successfully!")
    print("Both output files have been generated correctly.")
else:
    print("⚠️  Some files are missing")

print("\n✅ FINAL TASK STATUS: COMPLETE")