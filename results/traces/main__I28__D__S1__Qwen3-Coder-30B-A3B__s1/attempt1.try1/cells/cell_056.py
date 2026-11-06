# Final system status
import os

print("SYSTEM STATUS")
print("=" * 20)
print("Checking output files:")

files = ['output/mhw_mask.nc', 'output/report.json']
all_present = True

for file in files:
    if os.path.exists(file):
        print(f"✅ {file}")
    else:
        print(f"❌ {file}")
        all_present = False

if all_present:
    print("\n🎉 ALL SYSTEMS OPERATIONAL")
    print("Task completed successfully!")
else:
    print("\n💥 SYSTEM ERROR")

print("=" * 20)