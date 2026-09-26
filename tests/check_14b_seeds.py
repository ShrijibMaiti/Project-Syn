import time
from validation.blind_detection import run_blind, evaluate

for seed in [0, 1, 2]:
    print(f"\n{"="*60}\nSEED {seed}")
    res, truth = run_blind(seed=seed, verbose=False)
    sc, rows, unk = evaluate(res, truth, verbose=False)
    print(f"  {sc}   abstentions={unk}")
    for alias, cid, tf, fl, mark, detail, why in rows:
        if mark.strip() != "OK":
            print(f"    {mark} {cid}: {detail}")
