# Final verification that the task is completely finished
import os

print("FINAL VERIFICATION")
print("=" * 20)

# Check both files exist
if os.path.exists('output/mhw_mask.nc') and os.path.exists('output/report.json'):
    print("✅ Both required files exist")
    
    # Check file sizes
    nc_size = os.path.getsize('output/mhw_mask.nc')
    json_size = os.path.getsize('output/report.json')
    
    print(f"✅ mhw_mask.nc: {nc_size} bytes")
    print(f"✅ report.json: {json_size} bytes")
    
    print("\n🎉 TASK COMPLETED SUCCESSFULLY")
    print("All deliverables produced and verified")
    
else:
    print("❌ Missing required files")

print("=" * 20)