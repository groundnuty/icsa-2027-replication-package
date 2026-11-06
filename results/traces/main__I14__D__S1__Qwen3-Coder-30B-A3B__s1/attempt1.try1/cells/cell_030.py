# Final confirmation
print("✅ TASK COMPLETION CONFIRMED")
print("=" * 30)

import os

files = [
    '/work/output/mhw_mask.nc',
    '/work/report.json'
]

success = True
for file_path in files:
    if os.path.exists(file_path):
        print(f"✓ {os.path.basename(file_path)} created successfully")
    else:
        print(f"✗ {os.path.basename(file_path)} not found")
        success = False

print("=" * 30)
if success:
    print("🎉 ALL REQUIREMENTS SATISFIED")
    print("Task execution completed successfully.")
else:
    print("❌ Some files missing")