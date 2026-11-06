tgt=(dts>=pd.Timestamp("2020-06-01"))&(dts<=pd.Timestamp("2020-08-31"))
sea=np.isfinite(A[tgt]).all(axis=0)
print("sea cells",sea.sum(), "of",sea.size)
print("raw thr NaN per cell in sea:", np.isnan(thr[1:367][:,sea]).sum(), "clim:",np.isnan(clim[1:367][:,sea]).sum())
print("smoothed T NaN in sea:", np.isnan(T[:,sea]).sum(), "C:", np.isnan(C[:,sea]).sum())
print("cell-days with NaN in raw pool, sea:", np.isnan(thr[1:367][:,sea]).sum())
bad=np.isnan(A[:, :, :]).any(axis=0); print("cells with any NaN in full data:", bad.sum())
# which sea cells have NaN baseline? count finite values in baseline
fin=np.isfinite(A).sum(axis=0); print(fin[sea].min(), fin[~sea].max() if (~sea).any() else None)