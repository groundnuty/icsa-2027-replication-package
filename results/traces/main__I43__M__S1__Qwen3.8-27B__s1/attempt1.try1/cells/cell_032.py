import pickle
p = pickle.load(open("/tmp/pools.pkl","rb"))["pools"]
ks = sorted(p.keys())
print(type(ks[0]), ks[:5], ks[-5:])
print(197 in ks, 196 in ks, 198 in ks)
print([k for k in ks if 193 <= k <= 201])
print(len(ks))
