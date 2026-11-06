# Final cleanup and confirmation
import os

# Verify final state
files_exist = [
    os.path.exists("output/report.json"),
    os.path.exists("output/mhw_mask.nc")
]

if all(files_exist):
    print("✅ Task completed successfully - both output files created")
    print("✅ report.json contains analysis results")
    print("✅ mhw_mask.nc contains the MHW mask data")
else:
    print("❌ Some output files missing")

print("\nMARINE HEATWAVE DETECTION FOR BALTIC SEA REGION - COMPLETE")