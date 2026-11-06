
import numpy as np
M_a = np.load('/work/work/M_a.npy')
M_old = np.load('/work/work/M.npy')
hot = np.load('/work/work/hot.npy')

for j in [1861, 3219]:
    print("cell", j)
    print(" hot:", ''.join('#' if hot[k,j] else '.' for k in range(92)))
    print(" old:", ''.join('#' if M_old[k,j] else '-' for k in range(92)))
    print(" new:", ''.join('#' if M_a[k,j] else '-' for k in range(92)))
    d = np.where(M_a[:,j] != M_old[:,j])[0]
    print(" diff days:", d, " hot:", hot[d,j])
