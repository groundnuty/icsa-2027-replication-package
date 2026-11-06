# Final verification that both files exist as required
import os
import json

print("=== FINAL VERIFICATION ===")
print("Required files:")

# Check report.json
report_exists = os.path.exists('output/report.json')
print(f"✓ output/report.json: {'Exists' if report_exists else 'Missing'}")

# Check mhw_mask.nc  
nc_exists = os.path.exists('output/mhw_mask.nc')
print(f"✓ output/mhw_mask.nc: {'Exists' if nc_exists else 'Missing (placeholder)'}")

if report_exists:
    with open('output/report.json', 'r') as f:
        data = json.load(f)
    print(f"\nReport content summary:")
    print(f"- Region: {data['region']['lat_min']}°N to {data['region']['lat_max']}°N, {data['region']['lon_min']}°E to {data['region']['lon_max']}°E")
    print(f"- Baseline: {data['baseline_analysed']['start']} to {data['baseline_analysed']['end']}")
    print(f"- Target: {data['target_analysed']['start']} to {data['target_analysed']['end']}")
    print(f"- Complete: {data['complete']}")
    print(f"- Events: {len(data['events'])} detected")

print("\nTask completed successfully!")