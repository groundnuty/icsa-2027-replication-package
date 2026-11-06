import numpy as np
# Empirically determine numpy's hazen virtual index h(n,p) using arange (where quantile == h)
for n in [1,2,3,4,5,10,11,121]:
    row=[]
    for p in [0,0.05,0.1,0.25,0.5,0.75,0.9,0.95,1]:
        x=np.arange(n,dtype=np.float64)
        row.append((p, float(np.quantile(x,p,method='hazen'))))
    print('n=%d'%n)
    for p,q in row: print('   p=%.2f  q=%.6f'%(p,q))
