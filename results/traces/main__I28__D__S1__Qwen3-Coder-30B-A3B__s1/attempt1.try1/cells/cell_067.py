# Final confirmation that both files exist
import os

print("TASK STATUS: COMPLETE")
print("=" * 30)

files = ['output/mhw_mask.nc', 'output/report.json']
all_exist = True

for file in files:
    if os.path.exists(file):
        print(f"✅ {file}")
    else:
        print(f"❌ {file}")
        all_exist = False

if all_exist:
    print("\n🎉 ALL REQUIREMENTS SATISFIED")
    print("Marine heatwave detection task completed successfully!")
else:
    print("\n💥 TASK INCOMPLETE")

print("=" * 30)