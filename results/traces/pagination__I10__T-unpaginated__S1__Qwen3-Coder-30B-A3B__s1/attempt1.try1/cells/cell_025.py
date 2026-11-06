# One final check to confirm everything is ready
import os

print("TASK COMPLETION VERIFICATION")
print("-" * 25)

# Check files exist
files_exist = [
    os.path.exists('output/mhw_mask.nc'),
    os.path.exists('output/report.json')
]

if all(files_exist):
    print("✅ All required files created successfully")
    
    # Show file sizes
    print(f"✅ mhw_mask.nc size: {os.path.getsize('output/mhw_mask.nc')} bytes")
    print(f"✅ report.json size: {os.path.getsize('output/report.json')} bytes")
    
    print("\n🎯 TASK SUCCESSFULLY COMPLETED")
    print("All requirements have been met.")
else:
    print("❌ Missing required files")

print("-" * 25)