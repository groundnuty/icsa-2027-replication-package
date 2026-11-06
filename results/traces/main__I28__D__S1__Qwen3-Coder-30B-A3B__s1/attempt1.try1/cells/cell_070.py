# Final verification
import os

print("FINAL VERIFICATION")
print("=" * 25)

# Check that both files exist
files = ['output/mhw_mask.nc', 'output/report.json']

all_exist = True
for file in files:
    exists = os.path.exists(file)
    print(f"{file}: {'✅ FOUND' if exists else '❌ MISSING'}")
    if not exists:
        all_exist = False

if all_exist:
    print("\n🎉 TASK COMPLETED SUCCESSFULLY")
    print("Both required output files generated")
else:
    print("\n💥 TASK INCOMPLETE")

print("=" * 25)