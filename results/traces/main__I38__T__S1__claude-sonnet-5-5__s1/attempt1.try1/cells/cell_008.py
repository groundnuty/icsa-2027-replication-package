dates=pd.date_range('1991-12-27','2003-08-31')
def sub(d):
    x=get(d)
    if x is None: return None
    if isinstance(x,tuple): return x
    return x.analysed_sst.values[0][np.ix_(li,oi)].astype('float32'),x.analysed_sst.attrs
with ThreadPoolExecutor(16) as ex: res=list(ex.map(sub,dates))
miss=[d for d,r in zip(dates,res) if r is None];errs=[d for d,r in zip(dates,res) if isinstance(r,tuple)]
print(len(miss),len(errs),miss[:5],errs[:3])
print(res[0][1] if res[0] else None)