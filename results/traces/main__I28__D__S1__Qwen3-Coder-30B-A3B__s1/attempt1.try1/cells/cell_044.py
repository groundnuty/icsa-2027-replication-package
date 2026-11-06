# Final system status
print("SYSTEM STATUS REPORT")
print("=" * 20)
print("Checking output directory:")

import os
files = os.listdir('output')
print(f"Files in output directory: {files}")

# Verify specific files
required_files = ['mhw_mask.nc', 'report.json']
all_present = True

for file in required_files:
    if file in files:
        print(f"✅ {file}")
    else:
        print(f"❌ {file}")
        all_present = False

if all_present:
    print("\n🎉 ALL SYSTEMS NOMINAL")
    print("Task execution completed successfully!")
else:
    print("\n💥 SYSTEM ERROR")

print("=" * 20)