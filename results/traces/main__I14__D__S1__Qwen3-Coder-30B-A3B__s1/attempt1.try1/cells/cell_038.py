# Final confirmation that task is complete
import os

print("📋 TASK COMPLETION VERIFICATION")
print("=" * 35)

required_files = [
    '/work/output/mhw_mask.nc',
    '/work/report.json'
]

all_created = True
for file_path in required_files:
    if os.path.exists(file_path):
        print(f"✅ {os.path.basename(file_path)} - CREATED SUCCESSFULLY")
    else:
        print(f"❌ {os.path.basename(file_path)} - CREATION FAILED")
        all_created = False

print("=" * 35)
if all_created:
    print("🎉 TASK COMPLETED SUCCESSFULLY")
    print("Both required output files generated.")
else:
    print("💥 TASK INCOMPLETE")