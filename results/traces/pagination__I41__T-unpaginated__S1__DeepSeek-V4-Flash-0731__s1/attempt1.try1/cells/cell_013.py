
# Check if baseline_data is still available
try:
    print(f"baseline_data shape: {baseline_data.shape}")
    print(f"target_data shape: {target_data.shape}")
except NameError as e:
    print(f"Variable not available: {e}")
