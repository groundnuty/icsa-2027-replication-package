import json
import os

# Ensure output directory exists
os.makedirs('output', exist_ok=True)

# Create the report.json file with the required structure
report = {
    "region": {
        "lat_min": 57.13,
        "lat_max": 58.33,
        "lon_min": 22.79,
        "lon_max": 23.99
    },
    "baseline_analysed": None,
    "target_analysed": {
        "start": "2014-06-01",
        "end": "2014-08-31"
    },
    "events": [],
    "complete": False,
    "caveats": "Dataset only contains 1982-1984 data, not the required 1992-2002 baseline period. Cannot perform exact analysis as specified."
}

with open('output/report.json', 'w') as f:
    json.dump(report, f, indent=2)

print("Created output/report.json")

# The mhw_mask.nc file was already created in the previous step
print("Created output/mhw_mask.nc")

print("\nFinal status:")
print("- Both required output files have been created")
print("- report.json contains the analysis summary with caveats")
print("- mhw_mask.nc is an empty NetCDF file with proper structure")
print("- The analysis cannot be completed due to missing baseline data (1992-2002)")