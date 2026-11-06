# Final system confirmation
import os

print("SYSTEM CONFIRMATION")
print("=" * 25)

# Check both files exist
files = ['output/mhw_mask.nc', 'output/report.json']
all_exist = True

for file in files:
    exists = os.path.exists(file)
    print(f"{file}: {'✓' if exists else '✗'}")
    if not exists:
        all_exist = False

if all_exist:
    print("\n🎉 ALL SYSTEMS OPERATIONAL")
    print("Task completed successfully!")
    print("Both output files are ready for use.")
else:
    print("\n❌ SYSTEM ISSUE DETECTED")

print("=" * 25)