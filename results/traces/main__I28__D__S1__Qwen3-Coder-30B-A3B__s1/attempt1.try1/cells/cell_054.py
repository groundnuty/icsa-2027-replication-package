# Final verification that both files exist
import os

print("FINAL VERIFICATION")
print("=" * 20)

files_to_check = [
    'output/mhw_mask.nc',
    'output/report.json'
]

all_found = True
for file in files_to_check:
    if os.path.exists(file):
        size = os.path.getsize(file)
        print(f"✅ {file} ({size} bytes)")
    else:
        print(f"❌ {file}")
        all_found = False

if all_found:
    print("\n🎉 ALL FILES SUCCESSFULLY GENERATED")
    print("Task execution completed successfully!")
else:
    print("\n💥 SOME FILES MISSING")

print("=" * 20)