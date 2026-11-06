
import numpy as np

# Test numpy's hazen method with a simple array
arr = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], dtype=np.float64)
print("np.percentile(arr, 90, method='hazen'):", np.percentile(arr, 90, method='hazen'))

# Let me try to understand numpy's implementation
# N=10, p=0.9
# Try different formulas:
# Formula 1: h=(N-1)*p, Q=x[floor(h)]+(h-floor(h))*(x[floor(h)+1]-x[floor(h)])
N = 10
p = 0.9
h1 = (N-1)*p
k1 = int(np.floor(h1))
g1 = h1 - k1
if k1 >= N-1:
    q1 = arr[-1]
else:
    q1 = (1-g1)*arr[k1] + g1*arr[k1+1]
print(f"Formula 1 (h=(N-1)*p): h={h1}, k={k1}, g={g1}, Q={q1}")

# Formula 2: h=(N-1)*p+0.5
h2 = (N-1)*p + 0.5
k2 = int(np.floor(h2))
g2 = h2 - k2
if k2 >= N-1:
    q2 = arr[-1]
else:
    q2 = (1-g2)*arr[k2] + g2*arr[k2+1]
print(f"Formula 2 (h=(N-1)*p+0.5): h={h2}, k={k2}, g={g2}, Q={q2}")

# Formula 3: h=(N)*p
h3 = N*p
k3 = int(np.floor(h3))
g3 = h3 - k3
if k3 >= N-1:
    q3 = arr[-1]
else:
    q3 = (1-g3)*arr[k3] + g3*arr[k3+1]
print(f"Formula 3 (h=N*p): h={h3}, k={k3}, g={g3}, Q={q3}")

# Formula 4: h=(N-1)*p+1 (1-indexed), k=floor(h)-1 (0-indexed)
h4 = (N-1)*p + 1
k4 = int(np.floor(h4)) - 1
g4 = h4 - np.floor(h4)
if k4 >= N-1:
    q4 = arr[-1]
else:
    q4 = (1-g4)*arr[k4] + g4*arr[k4+1]
print(f"Formula 4 (h=(N-1)*p+1, k=floor(h)-1): h={h4}, k={k4}, g={g4}, Q={q4}")

# Let me check numpy's source implementation
print("\nLet me check numpy's implementation of hazen...")
print("From numpy docs, the formula is:")
print("h = (N-1) * p + 0.5")
h_np = (N-1)*p + 0.5
print(f"h = {h_np}")
k_np = int(np.floor(h_np))
g_np = h_np - np.floor(h_np)
print(f"k = {k_np}, g = {g_np}")
if k_np >= N-1:
    q_np = arr[-1]
else:
    q_np = (1-g_np)*arr[k_np] + g_np*arr[k_np+1]
print(f"Q = {q_np}")

# Compare with numpy
print(f"numpy result: {np.percentile(arr, 90, method='hazen')}")
