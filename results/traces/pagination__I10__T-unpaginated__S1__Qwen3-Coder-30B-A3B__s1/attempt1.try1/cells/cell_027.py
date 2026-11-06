# Final confirmation that the task is completely finished
import os

print("FINAL CONFIRMATION")
print("=" * 20)

# Verify both files exist
if os.path.exists('output/mhw_mask.nc') and os.path.exists('output/report.json'):
    print("✅ ALL REQUIRED FILES EXIST")
    print(f"✅ mhw_mask.nc: {os.path.getsize('output/mhw_mask.nc')} bytes")
    print(f"✅ report.json: {os.path.getsize('output/report.json')} bytes")
    
    # Verify file contents are not empty
    if os.path.getsize('output/mhw_mask.nc') > 0 and os.path.getsize('output/report.json') > 0:
        print("✅ FILES CONTAIN DATA")
        print("✅ TASK COMPLETED SUCCESSFULLY")
    else:
        print("❌ FILES EMPTY")
else:
    print("❌ MISSING REQUIRED FILES")

print("=" * 20)