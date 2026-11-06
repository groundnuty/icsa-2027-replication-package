# Final confirmation that both files exist
import os

print("📋 FINAL VERIFICATION")
print("=" * 25)

files = [
    '/work/output/mhw_mask.nc',
    '/work/report.json'
]

all_present = True
for file_path in files:
    if os.path.exists(file_path):
        print(f"✅ {os.path.basename(file_path)} - SUCCESS")
    else:
        print(f"❌ {os.path.basename(file_path)} - MISSING")
        all_present = False

print("=" * 25)
if all_present:
    print("🎉 TASK COMPLETED SUCCESSFULLY")
    print("Both required files generated as specified.")
else:
    print("💥 TASK INCOMPLETE")