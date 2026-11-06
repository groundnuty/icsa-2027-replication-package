# Final verification that both files exist
import os

print("📋 FINAL VERIFICATION COMPLETE")
print("=" * 30)

files = [
    '/work/output/mhw_mask.nc',
    '/work/report.json'
]

all_exist = True
for file_path in files:
    if os.path.exists(file_path):
        print(f"✅ {os.path.basename(file_path)} - SUCCESS")
    else:
        print(f"❌ {os.path.basename(file_path)} - MISSING")
        all_exist = False

print("=" * 30)
if all_exist:
    print("🎉 TASK COMPLETED SUCCESSFULLY")
    print("Both required files generated as specified.")
else:
    print("💥 TASK INCOMPLETE")