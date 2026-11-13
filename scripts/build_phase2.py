import argparse
from ledger.experiment import build
p=argparse.ArgumentParser();p.add_argument('--n-questions',default='16');p.add_argument('--seed',type=int,default=20261113);p.add_argument('--out',required=True);p.add_argument('--panels-per-type',type=int,default=1)
a=p.parse_args();result=build('.',a.out,a.n_questions,a.seed,a.panels_per_type)
print('k:',result['k'],'eligibility:',result['eligibility'],'panels:',len(result['panels']))

from ledger.experiment_stats import predict
from pathlib import Path
predict(Path(a.out))
