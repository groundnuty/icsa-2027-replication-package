def load(dates):
    out=[]
    for x in dates:
        with xr.open_dataset(f"{p}sst_{x:%Y%m%d}.nc",engine='h5netcdf') as a:
            out.append(a.analysed_sst.values[0][np.ix_(ii,jj)].astype('float64'))
    return np.array(out)
bd=pd.date_range('1991-12-27','2003-01-05')
B=load(bd)
td=pd.date_range('2009-06-01','2009-08-31')
T=load(td)
np.save('/tmp/B.npy',B);np.save('/tmp/T.npy',T)
print(B.shape,np.isnan(B).mean(),np.isnan(T).mean())