# Final system check
print("SYSTEM CHECK")
print("=" * 20)

import os

# Verify output files exist
files = ['output/mhw_mask.nc', 'output/report.json']
all_good = True

for file in files:
    if os.path.exists(file):
        size = os.path.getsize(file)
        print(f"✅ {file} ({size} bytes)")
    else:
        print(f"❌ {file}")
        all_good = False

if all_good:
    print("\n🎉 SYSTEM OPERATIONAL")
    print("Task execution completed successfully!")
else:
    print("\n💥 SYSTEM ERROR")

print("=" * 20)