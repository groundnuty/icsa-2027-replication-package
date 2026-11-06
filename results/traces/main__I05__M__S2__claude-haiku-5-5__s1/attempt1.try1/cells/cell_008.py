
# diagnostics: summer baseline mean vs 2021 mean, threshold vs climatology
m=(bt.month>=6)&(bt.month<=8)&inbase
print('baseline JJA mean SST (sea):', np.nanmean(flat[m][:,sea]), ' 2021 JJA:', np.nanmean(T[:,sea]))
print('thr-clim mean in summer:', np.nanmean((thrS-climS)[150:240][:,sea]))
# check one cell: raw pool for doy 170 (~Jun 19)
c=np.where(sea)[0][100]
print('cell thr doy170', thrS[169,c], 'clim', climS[169,c], 'obs 2021 Jun-Aug range', T[:,c].min(), T[:,c].max())
print('baseline JJA cell pct90', np.nanquantile(flat[m][:,c],0.9), 'mean', np.nanmean(flat[m][:,c]))
