# Final status check
import os

required_files = ['output/mhw_mask.nc', 'output/report.json']
all_present = all(os.path.exists(f) for f in required_files)

print(f"All required files present: {all_present}")
if all_present:
    print("✅ Task completed successfully!")
else:
    print("❌ Some files missing")