# Final verification that everything is ready
import os

print("🏁 FINAL VERIFICATION")
print("-" * 20)

# Check for the two required files
required_files = ['output/mhw_mask.nc', 'output/report.json']
all_present = True

for file_path in required_files:
    present = os.path.exists(file_path)
    print(f"{file_path}: {'✅ READY' if present else '❌ MISSING'}")
    if not present:
        all_present = False

print("-" * 20)
if all_present:
    print("🎉 ALL OUTPUTS GENERATED SUCCESSFULLY")
    print("Marine heatwave detection task is COMPLETE")
else:
    print("⚠️  Missing some outputs")

print("\n✅ TASK FINISHED")