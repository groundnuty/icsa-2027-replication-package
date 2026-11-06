import numpy as np
st3 = np.load('/tmp/stage3.npz')
hot, A, B = st3['hot'], st3['A'], st3['B']
nt, NC = hot.shape
cc = 285
b = hot[:,cc]
print("hot seq cell 285:", ''.join('1' if x else '0' for x in b))
a_vec = A[:,cc]; b_vec = B[:,cc]
print("A   :", ''.join('1' if x else '0' for x in a_vec))
print("B   :", ''.join('1' if x else '0' for x in b_vec))

def brute_A(b):
    n=len(b); mhw=[False]*n
    runs=[]; i=0
    while i<n:
        if b[i]:
            j=i
            while j+1<n and b[j+1]: j+=1
            runs.append((i,j)); i=j+1
        else: i+=1
    print("  runs:", runs)
    cores=[(a,e) for a,e in runs if e-a+1>=5]
    print("  cores:", cores)
    for a,e in cores:
        for t in range(a,e+1): mhw[t]=True
    for (a1,e1),(a2,e2) in zip(cores,cores[1:]):
        gap = a2-e1-1
        if gap<=2:
            for t in range(e1+1,a2): mhw[t]=True
    return mhw
br = brute_A(b)
print("brA :", ''.join('1' if x else '0' for x in br))
print("equal?", np.array_equal(np.array(br), a_vec))
