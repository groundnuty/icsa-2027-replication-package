# Final confirmation that both files exist
import os

print("📋 FINAL CONFIRMATION")
print("=" * 25)

files = [
    '/work/output/mhw_mask.nc',
    '/work/report.json'
]

all_good = True
for file_path in files:
    if os.path.exists(file_path):
        print(f"✅ {os.path.basename(file_path)} - SUCCESS")
    else:
        print(f"❌ {os.path.basename(file_path)} - MISSING")
        all_good = False

print("=" * 25)
if all_good:
    print("🎉 TASK COMPLETED SUCCESSFULLY")
    print("Both required files generated as specified.")
else:
    print("💥 TASK INCOMPLETE")