import numpy as np, pickle
with open('/tmp/stepB.pkl','rb') as fh: B1 = pickle.load(fh)
with open('/tmp/stepB2.pkl','rb') as fh: B2 = pickle.load(fh)
with open('/tmp/stepA.pkl','rb') as fh: A1 = pickle.load(fh)
with open('/tmp/stepA2.pkl','rb') as fh: A2 = pickle.load(fh)
print("hot masks identical:", np.array_equal(B1['hot'], B2['hot']))
print("mhw masks identical:", np.array_equal(B1['mhw'], B2['mhw']))
h1 = B1['hot'].reshape(92,-1); h2 = B2['hot'].reshape(92,-1)
print("hot-day flips:", int((h1 ^ h2).sum()))
d = A2['thresh_s'] - A1['thresh_s']
print("thresh delta in target doy band: min %.4f max %.4f" % (d[152:244].min(), d[152:244].max()))
# how close are SSTs to thresholds where deltas exist (target band, sea cells)?
sst = A2['sst'].reshape(92,-1); sea = A2['sea']; tdoy = A2['tdoy']
band = (tdoy >= 153) & (tdoy <= 244)
margins = np.abs(sst[band][:, sea] - A2['thresh_s'][tdoy[band]-1][:, sea])
print("min |sst - thresh| margin over target band & sea cells:", margins.min(), "K")
print("count of margins < 0.07 K:", int((margins < 0.07).sum()), "of", margins.size)
