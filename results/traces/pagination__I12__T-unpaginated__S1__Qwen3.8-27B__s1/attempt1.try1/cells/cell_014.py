import numpy as np
x = np.arange(396*3600, dtype=np.float64).reshape(396, 3600)
w = np.lib.stride_tricks.sliding_window_view(x, 31, axis=0)
print('swv shape:', w.shape)
print('mean axis1:', w.mean(axis=1).shape)
# alternative: explicit window shape tuple
w2 = np.lib.stride_tricks.sliding_window_view(x, (31,), axis=(0,))
print('swv tuple shape:', w2.shape)