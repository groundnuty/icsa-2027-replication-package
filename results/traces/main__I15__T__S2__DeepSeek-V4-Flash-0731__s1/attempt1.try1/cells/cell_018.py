
import numpy as np

threshold = np.load('threshold_raw.npy')
climatology = np.load('climatology_raw.npy')

# threshold has shape (367, n_lat, n_lon), where index 0 is unused and index 1-366 = DOY 1-366

def smooth_wrap(arr, window=31, doy_len=366):
    """Smooth a 366-element array (index 1..366) with centred moving average wrapping around.
    arr has shape (367, n_lat, n_lon). Returns smoothed array of same shape.
    Day d averages days d-15..d+15 modulo 366.
    """
    n_lat, n_lon = arr.shape[1], arr.shape[2]
    smoothed = np.full_like(arr, np.nan)
    half = window // 2  # 15
    
    # Extract the 366 values for each cell
    for i in range(n_lat):
        for j in range(n_lon):
            vals = arr[1:367, i, j]  # indices 0-365 correspond to DOY 1-366
            smoothed_vals = np.zeros(366)
            for d in range(1, 367):  # d = 1..366 (DOY)
                # Sum over d-15 to d+15 modulo 366
                indices = []
                for offset in range(-half, half + 1):
                    dd = ((d - 1 + offset) % 366) + 1  # DOY index in 1..366
                    indices.append(dd)
                vals_for_avg = [vals[dd - 1] for dd in indices]
                # Count non-NaN
                valid = [v for v in vals_for_avg if not np.isnan(v)]
                if len(valid) > 0:
                    smoothed_vals[d - 1] = np.mean(valid)
                else:
                    smoothed_vals[d - 1] = np.nan
            smoothed[1:367, i, j] = smoothed_vals
    return smoothed

# This is slow. Let me vectorize it.
