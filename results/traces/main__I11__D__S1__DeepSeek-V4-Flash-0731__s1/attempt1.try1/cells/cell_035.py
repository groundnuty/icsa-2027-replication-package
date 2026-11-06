
import numpy as np

# Test hazen with different data
data = np.array([10.0, 20.0, 30.0, 40.0, 50.0, 60.0])
for p in [0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0]:
    q_hazen = np.quantile(data, p, method='hazen')
    q_linear = np.quantile(data, p)
    print(f"p={p}: hazen={q_hazen}, linear={q_linear}")

print()

# Check with specific values
data2 = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
print("Data: [1, 2, 3, 4, 5]")
for p in [0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0]:
    q_hazen = np.quantile(data2, p, method='hazen')
    q_linear = np.quantile(data2, p)
    print(f"p={p}: hazen={q_hazen}, linear={q_linear}")
