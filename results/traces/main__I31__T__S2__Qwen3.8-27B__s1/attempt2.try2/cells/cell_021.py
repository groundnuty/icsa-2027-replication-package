import numpy as np

def runs(b):
    d = np.diff(b.astype(np.int8))
    return np.where(d == 1)[0], np.where(d == -1)[0]

h1 = np.array([True]*5 + [False]*1 + [True]*5 + [False]*3 + [True]*6)
T = len(h1)
inm = np.zeros(T, bool)
s_, e_ = runs(np.concatenate(([False], h1, [False])))
print("hot runs:", list(zip(s_.tolist(), e_.tolist())))
for a, b in zip(s_, e_):
    if b - a >= 5:
        inm[a:b] = True
print("inm after pass1:", inm.astype(int).tolist())
b2 = np.concatenate(([True], ~inm, [True]))
print("b2:", b2.astype(int).tolist())
d2 = np.diff(b2.astype(np.int8))
print("d2:", d2.tolist())
gs, ge = runs(b2)
print("gs:", gs.tolist(), "ge:", ge.tolist())
for a, b in zip(gs, ge):
    cond = (b - a) in (1, 2) and a > 0 and bool(inm[a - 1]) and b < T and bool(inm[b])
    print(f"gap ({a},{b}) len={b-a} cond={cond}")
    if cond:
        inm[a:b] = True
print("final:", inm.astype(int).tolist())
