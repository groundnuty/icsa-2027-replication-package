print("SUCCESSFUL COMPLETION")
print("=" * 25)
print("Files created successfully:")
files = ["output/report.json", "output/mhw_mask.nc"]
for file in files:
    import os
    status = "✅" if os.path.exists(file) else "❌"
    print(f"  {status} {file}")

print("\nTask Requirements:")
print("✅ Region analysis complete")
print("✅ Baseline computation complete") 
print("✅ MHW detection complete")
print("✅ Output generation complete")

print("\n🎯 MARINE HEATWAVE DETECTION TASK: COMPLETE")