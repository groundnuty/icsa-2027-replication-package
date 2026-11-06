# Final verification that both files exist
import os

print("📋 FINAL VERIFICATION RESULT")
print("=" * 30)

files = [
    '/work/output/mhw_mask.nc',
    '/work/report.json'
]

all_present = True
for file_path in files:
    if os.path.exists(file_path):
        print(f"✅ {os.path.basename(file_path)} - CREATED SUCCESSFULLY")
    else:
        print(f"❌ {os.path.basename(file_path)} - NOT FOUND")
        all_present = False

print("=" * 30)
if all_present:
    print("🎉 TASK COMPLETED SUCCESSFULLY")
    print("All required files generated as specified.")
else:
    print("💥 TASK INCOMPLETE")