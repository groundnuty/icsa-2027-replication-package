import pickle,numpy as np
dates,res=pickle.load(open('/tmp/cache.pkl','rb'))
S=np.stack([r[1] for r in res]).astype('float64')
T=S[-92:];B=S[:-92]
print(np.nanmean(B,(1,2))[:3],np.nanmean(T,(1,2))[::10])
print(np.isnan(S).mean((1,2))[[0,100,2000,-1]], T.dtype)