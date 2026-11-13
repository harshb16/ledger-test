"""Build nested panels and reuse the frozen all-162-id grouped-CV benchmark fit."""
from ledger.experiment_v2 import build_v2
from ledger.experiment_stats import predict
from pathlib import Path
import shutil
out=Path('results/phase3/build')
p=build_v2(out=out)
print('panels',len(p['panels']))
# The benchmark training design/seed/k are unchanged: all 162 ids, grouped CV.
shutil.copy2('results/phase2/pilot/stat_hyperparameters.json',out/'stat_hyperparameters.json')
predict(out,fit=False)
