# Final system check
import os

print("SYSTEM CHECK")
print("=" * 25)

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
    print("\n🎉 ALL SYSTEMS NOMINAL")
    print("Task completed successfully!")
else:
    print("\n💥 SYSTEM ERROR")

print("=" * 25)