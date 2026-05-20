import pandas as pd
from pathlib import Path

subs = [
    "2100-01-01",
    "2100-01-02",
    "2100-01-03",
]

out = Path("data/input/rfwcc/test_rfwcc.xlsx")
out.parent.mkdir(parents=True, exist_ok=True)

df = pd.DataFrame(subs)
df.to_excel(out, index=False, header=["SubsystemID"]) 

print(f"Wrote {out.resolve()}")
