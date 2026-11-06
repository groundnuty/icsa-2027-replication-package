import numpy as np
from datetime import date, timedelta
S_base = np.load('/work/S_base.npy')
S_tgt = np.load('/work/S_tgt.npy')

# sea cells: finite on every target day
fin_tgt = np.isfinite(S_tgt)  # (92, 60, 60)
sea = fin_tgt.all(axis=0)  # (60, 60)
print("sea cells:", sea.sum(), "of", sea.size)

# is finiteness constant in time?
tgt_mask_varies = (fin_tgt.sum(axis=0) != 92) & (fin_tgt.sum(axis=0) != 0)
print("target cells with mixed finiteness:", tgt_mask_varies.sum())
b_finite = np.isfinite(S_base).sum(axis=0)
print("baseline mixed (0 < fin < 4028):", ((b_finite > 0) & (b_finite < 4028)).sum())
print("cells finite all baseline days:", (b_finite == 4028).sum())
# sea cells must be finite all baseline days?
print("sea cells finite all baseline:", (b_finite[sea] == 4028).all())

# check numpy version for method='hazen'
import numpy
print("numpy", numpy.__version__)
x = np.array([1.,2.,3.,4.])
print("hazen p90 check:", np.quantile(x, 0.9, method='hazen'))
