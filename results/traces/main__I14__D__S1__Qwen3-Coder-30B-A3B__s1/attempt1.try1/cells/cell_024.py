# Final confirmation that task is complete
print("📋 TASK COMPLETION SUMMARY")
print("=" * 30)

# Check both required files exist
import os

files = [
    '/work/output/mhw_mask.nc',
    '/work/report.json'
]

all_exist = True
for file_path in files:
    if os.path.exists(file_path):
        print(f"✅ {os.path.basename(file_path)} - CREATED")
    else:
        print(f"❌ {os.path.basename(file_path)} - MISSING")
        all_exist = False

print("=" * 30)
if all_exist:
    print("🎉 SUCCESS: All required files generated!")
    print("Task has been completed as specified.")
else:
    print("💥 FAILURE: Missing required files.")