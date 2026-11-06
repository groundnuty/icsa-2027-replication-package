# Final system check
print("SYSTEM CHECK")
print("=" * 20)

import os

# Check for required files
required_files = ['output/mhw_mask.nc', 'output/report.json']

print("Checking output directory:")
for file in required_files:
    exists = os.path.exists(file)
    print(f"  {file}: {'✓' if exists else '✗'}")

# Verify they're actually files (not directories)
all_good = True
for file in required_files:
    if os.path.exists(file) and not os.path.isdir(file):
        size = os.path.getsize(file)
        print(f"  Size: {size} bytes")
    else:
        print(f"  Error: {file} is not a valid file")
        all_good = False

if all_good:
    print("\n✅ ALL SYSTEMS NOMINAL")
    print("Task execution completed successfully!")
else:
    print("\n❌ SYSTEM ERROR")

print("=" * 20)