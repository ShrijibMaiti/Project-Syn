import numpy as np
from synthesis.simulator import RetryLoopTwin

twin = RetryLoopTwin()
print("cold-start settled value vs number of iteration steps")
print(f"{"load":>6}" + "".join(f"{s:>10}" for s in [100, 500, 1000, 3000, 10000]))
for L in [3.5, 3.7, 3.8, 3.9]:
    row = f"{L:>6.2f}"
    for s in [100, 500, 1000, 3000, 10000]:
        row += f"{float(twin.settle(np.array([0.0]), L, steps=s)[0]):>10.2f}"
    print(row)

print("\nis 2.68 actually a fixed point at load 3.8?  (f(p) - p should be ~0)")
for p in [2.68, 100.0]:
    nxt = float(twin.step(np.array([p]), 3.8)[0])
    print(f"  p={p:>6.2f}  f(p)={nxt:>8.4f}  residual={nxt - p:+.6f}")

print("\ntrajectory from q=0 at load 3.8 (first 12 steps):")
q = 0.0
traj = []
for _ in range(12):
    q = float(twin.step(np.array([q]), 3.8)[0])
    traj.append(round(q, 3))
print(" ", traj)
