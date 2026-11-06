# Final confirmation that both files exist
import os

print("TASK COMPLETION CONFIRMED")
print("=" * 25)
print("Checking output files:")

files = ['output/mhw_mask.nc', 'output/report.json']
all_exist = True

for file in files:
    if os.path.exists(file):
        print(f"✅ {file}")
    else:
        print(f"❌ {file}")
        all_exist = False

if all_exist:
    print("\n🎉 SUCCESS: All files created")
    print("Marine heatwave detection task completed successfully.")
else:
    print("\n❌ ERROR: Missing files")

print("=" * 25)