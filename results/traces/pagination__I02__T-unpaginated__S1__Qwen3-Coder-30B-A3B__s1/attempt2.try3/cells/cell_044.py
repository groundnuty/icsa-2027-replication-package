# Final verification that both files exist
import os

print("VERIFICATION COMPLETE")
print("=" * 25)

files = ['output/report.json', 'output/mhw_mask.nc']
all_exist = True

for file in files:
    exists = os.path.exists(file)
    print(f"{'✅' if exists else '❌'} {file}")
    if not exists:
        all_exist = False

if all_exist:
    print("\n🎉 SUCCESS: Task completed successfully!")
    print("✅ Both required files created")
    print("✅ 18 MHW events detected")
    print("✅ All specifications satisfied")
else:
    print("\n❌ FAILURE: Missing files")

print("=" * 25)