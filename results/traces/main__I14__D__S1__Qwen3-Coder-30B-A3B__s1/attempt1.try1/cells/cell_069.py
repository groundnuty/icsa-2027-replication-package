# Final confirmation that both files exist
import os

print("📋 FINAL STATUS")
print("=" * 20)

files = [
    '/work/output/mhw_mask.nc',
    '/work/report.json'
]

all_present = True
for file_path in files:
    if os.path.exists(file_path):
        print(f"✅ {os.path.basename(file_path)} - PRESENT")
    else:
        print(f"❌ {os.path.basename(file_path)} - MISSING")
        all_present = False

print("=" * 20)
if all_present:
    print("🎉 TASK COMPLETED SUCCESSFULLY")
    print("Both required files generated.")
else:
    print("💥 TASK INCOMPLETE")