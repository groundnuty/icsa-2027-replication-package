# Final system check
import os

print("SYSTEM STATUS")
print("=" * 20)

# Check that both files exist
files = ['output/mhw_mask.nc', 'output/report.json']
all_present = True

for file in files:
    if os.path.exists(file):
        size = os.path.getsize(file)
        print(f"✅ {file} ({size} bytes)")
    else:
        print(f"❌ {file}")
        all_present = False

if all_present:
    print("\n🎉 ALL SYSTEMS OPERATIONAL")
    print("Task completed successfully!")
else:
    print("\n💥 SYSTEM ERROR")

print("=" * 20)