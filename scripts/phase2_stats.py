import sys
from pathlib import Path
from ledger.experiment_stats import predict
predict(Path(sys.argv[1]))
