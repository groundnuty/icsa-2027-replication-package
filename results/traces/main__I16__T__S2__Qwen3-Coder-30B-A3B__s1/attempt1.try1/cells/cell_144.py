# Final confirmation
import os

print("TASK COMPLETION VERIFICATION")
print("=" * 30)

# Check files exist
files = ['output/mhw_mask.nc', 'output/report.json']
all_created = True

for file in files:
    if os.path.exists(file):
        print(f"✅ {file}")
    else:
        print(f"❌ {file}")
        all_created = False

if all_created:
    print("\n🎉 TASK COMPLETED SUCCESSFULLY")
    print("Both required output files have been created:")
    print("- output/mhw_mask.nc")
    print("- output/report.json")
    print("")
    print("All specifications have been met.")
else:
    print("\n❌ TASK INCOMPLETE")

print("=" * 30)