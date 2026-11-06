
print(np.nanmin(tvals[:, sea]), np.nanmax(tvals[:, sea]), np.nanmean(tvals[:,sea]))
print(np.nanmin(bvals), np.nanmax(bvals))
ex=(tvals-thr_s[tdoy])[:,sea]
print('max exceed',np.nanmax(ex), 'frac>=thr',np.mean(ex>=0))
print(thr_s[tdoy][:,sea].mean(), thr_s[150:160].mean(axis=(1,2)))
