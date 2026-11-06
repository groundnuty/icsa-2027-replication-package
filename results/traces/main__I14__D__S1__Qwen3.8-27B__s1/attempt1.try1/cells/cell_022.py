import numpy as np
thr = np.load('/work/data/thr_raw.npy').copy()
thr[59] = 0.5*(thr[58] + thr[60])
A2 = np.concatenate([thr[-15:], thr, thr[:15]], axis=0)
W = np.lib.stride_tricks.sliding_window_view(A2, 31, axis=0)
print("W shape:", W.shape)
c = 0
manual = np.mean([thr[(0+k) % 366, c] for k in range(-15, 16)])
print("naive i=0 col0:", manual)
print("A2[0:31,0] mean:", np.mean(A2[0:31, c]))
print("W[0,c,:] mean:", np.mean(W[0, c, :]))
print("W[0,c,:] == A2[0:31,c]?", np.array_equal(W[0, c, :], A2[0:31, c]))
print("first window elements:", W[0, c, :6], "...", A2[0, c], A2[14, c], A2[15, c])
print("thr[351,0], thr[0,0], thr[15,0]:", thr[351,0], thr[0,0], thr[15,0])