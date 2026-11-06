
import numpy as np
print(f'numpy version: {np.__version__}')

y = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])

# Check what hazen actually computes
# Let me manually implement what I think hazen should do
N = len(y)
p = 0.9

# Type 5 (hazen): 
# Position in 1-indexed: (N+1)*p
# j = floor((N+1)*p) = floor(11*0.9) = floor(9.9) = 9
# g = 0.9
# Q = (1-g)*x_j + g*x_{j+1} where x is 1-indexed
# x_9 = y[8] = 9, x_10 = y[9] = 10
# Q = 0.1*9 + 0.9*10 = 0.9 + 9 = 9.9

# But numpy gives 9.5. Let me check if numpy is using a different formula.

# Maybe numpy uses: position = (N-1)*p + 1 in 1-indexed, or equivalently (N-1)*p in 0-indexed
# position (0-indexed) = 9*0.9 = 8.1
# j = 8, g = 0.1
# Q = 0.9*y[8] + 0.1*y[9] = 0.9*9 + 0.1*10 = 8.1 + 1 = 9.1

# That's what method='linear' gives. Not hazen.

# Let me try: position (0-indexed) = N*p
# 10*0.9 = 9
# Q = y[9] = 10

# Or: position (0-indexed) = (N+1)*p - 1 = 8.9
# j=8, g=0.9
# Q = 0.1*y[8] + 0.9*y[9] = 0.9 + 9 = 9.9

# Or: position (0-indexed) = N*p - 1 = 8
# Q = y[8] = 9

# None of these give 9.5. Let me check what midpoint gives:
# midpoint: (lower + higher)/2
# lower: floor((N-1)*p) = floor(9*0.9) = floor(8.1) = 8, y[8] = 9
# higher: ceil((N-1)*p) = 9, y[9] = 10
# midpoint: (9+10)/2 = 9.5

# So numpy's hazen gives the same as midpoint? That seems wrong.

# Let me check if numpy's hazen is actually implementing the right formula
# Let me look at the numpy documentation for hazen method

# From numpy docs:
# hazen: Type 5
# The following formula is used:
# (1-g)x[j] + g x[j+1] where j = floor(Np) and g = Np - j

# Wait, maybe it's j = floor(Np) and not floor((N+1)p)?
# N*p = 10*0.9 = 9
# j = 9, g = 0
# Q = y[9] = 10

# That doesn't give 9.5 either.

# Let me just check empirically what hazen does
print(f'hazen: {np.percentile(y, 90, method="hazen")}')

# Let me try different p values and N values to understand the formula
for N_val in range(4, 12):
    z = np.arange(1, N_val+1, dtype=float)
    for p_val in [0.5, 0.75, 0.9]:
        result = np.percentile(z, p_val*100, method='hazen')
        print(f'N={N_val}, p={p_val}: hazen={result}')
    print()
