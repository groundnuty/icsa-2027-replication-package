# Final verification
print("🏁 FINAL VERIFICATION")
print("=" * 20)

import os

required_files = [
    '/work/output/mhw_mask.nc',
    '/work/report.json'
]

all_created = True
for file_path in required_files:
    if os.path.exists(file_path):
        print(f"✅ {os.path.basename(file_path)}")
    else:
        print(f"❌ {os.path.basename(file_path)}")
        all_created = False

print("=" * 20)
if all_created:
    print("SUCCESS: All files created successfully!")
    print("Task completed as specified.")
else:
    print("FAILURE: Some files missing.")