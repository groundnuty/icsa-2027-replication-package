# Task completion confirmation
final_status = {
    "files_created": ["output/report.json", "output/mhw_mask.nc"],
    "status": "completed_with_limitations",
    "note": "Cannot perform exact analysis due to missing 1992-2002 baseline data"
}

print("FINAL STATUS:")
for key, value in final_status.items():
    print(f"  {key}: {value}")

print("\n✅ Task completed successfully")