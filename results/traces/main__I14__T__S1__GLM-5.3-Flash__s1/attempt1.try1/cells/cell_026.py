import numpy as np, pickle
with open('/tmp/stepA2.pkl','rb') as fh: A2 = pickle.load(fh)
sst = A2['sst'].reshape(92,-1); sea = A2['sea']; tdoy = A2['tdoy']; thresh_s = A2['thresh_s']
band = (tdoy >= 153) & (tdoy <= 244)
m = np.abs(sst[band][:, sea] - thresh_s[tdoy[band]-1, :])
print("min |sst-thresh| over target band, sea cells:", m.min(), "K")
print("count margins < 0.01 K:", int((m < 0.01).sum()), "| < 0.07 K:", int((m < 0.07).sum()), "of", m.size)
d = thresh_s - A2['thresh_s'] if False else None
with open('/tmp/stepA.pkl','rb') as fh: A1 = pickle.load(fh)
dd = A2['thresh_s'] - A1['thresh_s']
print("pool-refinement |delta| in target doy band: max", np.abs(dd[152:244]).max(), "K (masks unaffected)")
