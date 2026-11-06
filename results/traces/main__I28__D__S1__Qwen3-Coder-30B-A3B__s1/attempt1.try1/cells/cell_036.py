# Final system status
print("SYSTEM STATUS")
print("=" * 20)
print("Checking output files...")

import os

files = ['output/mhw_mask.nc', 'output/report.json']
all_present = True

for file in files:
    if os.path.exists(file):
        print(f"✅ {file}")
    else:
        print(f"❌ {file}")
        all_present = False

if all_present:
    print("\n🎉 ALL FILES PRESENT - TASK COMPLETE")
else:
    print("\n💥 SOME FILES MISSING")

print("=" * 20)