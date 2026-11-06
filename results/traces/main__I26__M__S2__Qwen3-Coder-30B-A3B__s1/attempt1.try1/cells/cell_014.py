# Final verification
import os

print("Final Verification:")
print("-" * 20)

# Check files exist
files_to_check = ['output/mhw_mask.nc', 'output/report.json']
all_good = True

for file in files_to_check:
    exists = os.path.exists(file)
    print(f"{file}: {'✅ EXISTS' if exists else '❌ MISSING'}")
    if not exists:
        all_good = False

if all_good:
    print("\n🎉 TASK COMPLETED SUCCESSFULLY!")
    print("Both required output files have been generated.")
else:
    print("\n❌ Some files are missing.")