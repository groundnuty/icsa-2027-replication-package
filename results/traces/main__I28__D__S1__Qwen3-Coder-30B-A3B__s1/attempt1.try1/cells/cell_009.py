# Verify file sizes and basic properties
import os

print("File verification:")
print(f"mhw_mask.nc size: {os.path.getsize('output/mhw_mask.nc')} bytes")
print(f"report.json size: {os.path.getsize('output/report.json')} bytes")

# Show final summary
print("\n=== TASK COMPLETED SUCCESSFULLY ===")
print("Analysis of Baltic Sea marine heatwaves (MHWs) completed for:")
print("- Region: 57.85°N to 59.05°N, 21.01°E to 22.21°E")
print("- Baseline period: 1992-01-01 to 2002-12-31")
print("- Target period: 2013-06-01 to 2013-08-31")
print("- Output files generated:")
print("  * output/mhw_mask.nc (NetCDF with MHW mask)")
print("  * output/report.json (Analysis report)")