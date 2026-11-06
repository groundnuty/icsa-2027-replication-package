# Final verification that both files exist
import os

print("FINAL VERIFICATION")
print("=" * 25)

files = ['output/mhw_mask.nc', 'output/report.json']

all_exist = True
for file in files:
    if os.path.exists(file):
        size = os.path.getsize(file)
        print(f"✅ {file} ({size} bytes)")
    else:
        print(f"❌ {file}")
        all_exist = False

if all_exist:
    print("\n🎉 TASK COMPLETED SUCCESSFULLY")
    print("Both output files generated as required")
else:
    print("\n💥 TASK INCOMPLETE")

print("=" * 25)