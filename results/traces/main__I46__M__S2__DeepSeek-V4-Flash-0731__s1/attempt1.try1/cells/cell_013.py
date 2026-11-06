
import numpy as np

# Load saved data
threshold_raw = np.load('/tmp/threshold_raw.npy')
climatology_raw = np.load('/tmp/climatology_raw.npy')

print("threshold_raw shape:", threshold_raw.shape)
print("climatology_raw shape:", climatology_raw.shape)

# Check for NaN in raw thresholds
print("NaN count in threshold_raw:", np.isnan(threshold_raw).sum())
print("NaN count in climatology_raw:", np.isnan(climatology_raw).sum())
print("Total cells:", 366*60*60)
