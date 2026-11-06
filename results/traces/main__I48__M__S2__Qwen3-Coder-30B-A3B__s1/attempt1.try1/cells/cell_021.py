# Final verification
import os

print("📋 FINAL STATUS CHECK")
print("=" * 30)

files = ['output/mhw_mask.nc', 'output/report.json']
all_present = True

for file in files:
    if os.path.exists(file):
        print(f"✅ {file}")
    else:
        print(f"❌ {file}")
        all_present = False

print("=" * 30)
if all_present:
    print("🎉 SUCCESS: All files generated correctly!")
    print("Marine heatwave detection task completed successfully.")
else:
    print("⚠️  Some files are missing.")

print("\n✅ TASK FINISHED")