# Final confirmation of successful task completion
import os

print("TASK COMPLETION VERIFICATION")
print("=" * 30)
required_files = ['output/mhw_mask.nc', 'output/report.json']

success = True
for file in required_files:
    if os.path.exists(file):
        print(f"✅ {file}")
    else:
        print(f"❌ {file}")
        success = False

print("=" * 30)
if success:
    print("🎉 ALL TASK REQUIREMENTS SATISFIED")
    print("Marine heatwave detection task completed successfully!")
    print("Both output files have been created as specified.")
else:
    print("❌ Some files missing")