# Final confirmation that both files exist
import os

print("📋 FINAL CONFIRMATION")
print("=" * 20)

files = [
    '/work/output/mhw_mask.nc',
    '/work/report.json'
]

all_exist = True
for file_path in files:
    exists = os.path.exists(file_path)
    print(f"{'✅' if exists else '❌'} {os.path.basename(file_path)}")
    if not exists:
        all_exist = False

print("=" * 20)
if all_exist:
    print("🎉 TASK COMPLETED SUCCESSFULLY!")
    print("Both required files have been generated.")
else:
    print("❌ Some files are missing.")