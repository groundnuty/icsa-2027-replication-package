# Final verification that both required files exist
import os

success = True
if not os.path.exists('output/mhw_mask.nc'):
    print("ERROR: mhw_mask.nc not created")
    success = False
if not os.path.exists('output/report.json'):
    print("ERROR: report.json not created")
    success = False

if success:
    print("✅ Both required files successfully created!")
    print("Task completion confirmed.")
else:
    print("❌ Some files missing")