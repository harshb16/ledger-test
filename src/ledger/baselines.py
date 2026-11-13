"""Grouped cross-validation with fold exclusions applied to every ledger."""
import itertools
import numpy as np
import pandas as pd
from scipy.special import expit, logit, softmax
from .ledger import construct, KEY

A = [0.5,1.,1.5,2.]
LAM = [0.,1.,4.,16.,64.]
K = [0.,5.,20.]

def aggregate(p, method, scores=None, n=None, population=0., a=1., lam=0., k=0.):
    p = np.asarray(p)
    if method=='mean': return p.mean()
    if method=='median': return np.median(p)
    if method=='extremized_logit_mean': return expit(a*logit(np.clip(p,.01,.99)).mean())
    if method.startswith('best'): return p[np.argmin(scores)]
    shrunk = np.asarray(n)/(np.asarray(n)+k)*np.asarray(scores)+k/(np.asarray(n)+k)*population
    return softmax(-lam*shrunk)@p

def evaluate(data, panels, regime, seed, minimum=5, ledger_cache=None):
    if ledger_cache is None: ledger_cache = {}
    if panels.empty: return pd.DataFrame(),[]
    ids = np.array(sorted(panels.question_id.unique()))
    folds = np.array_split(np.random.default_rng(seed).permutation(ids),5)
    predictions, choices = [], []
    methods = ['mean','median','extremized_logit_mean','best_historical_raw','best_historical_adj','best_historical_fe','perf_weighted_raw','perf_weighted_adj','perf_weighted_fe']
    for fold, test in enumerate(folds):
        cache = {}
        for q in ids:
            key = (regime,q,tuple(sorted(test)))
            if key not in ledger_cache:
                ledger_cache[key] = construct(data,q,excluded=test,regime=regime)
            cache[q] = ledger_cache[key]
        rows = []
        for (q,draw), panel in panels.groupby(['question_id','draw']):
            led = cache[q]
            joined = panel.merge(led,on=KEY,suffixes=('_panel',''))
            # Preserve the sampled panel; no replacements based on skill or outcomes.
            if len(joined)!=5 or (joined.n_ids<minimum).any(): continue
            rows.append((q,draw,joined,led))
        if not rows: continue
        probabilities = np.stack([r[2].forecast.to_numpy() for r in rows])
        outcomes = np.array([r[2].outcome.iloc[0] for r in rows])
        sizes = np.stack([r[2].n_ids.to_numpy() for r in rows])
        test_mask = np.array([r[0] in test for r in rows])
        for method in methods:
            score = 'peer' if method.endswith('adj') else 'fe' if method.endswith('fe') else 'raw'
            scores = np.stack([r[2][score].to_numpy() for r in rows])
            population = np.array([r[3][score].mean() for r in rows])[:,None]
            grid = [{'a':a} for a in A] if method=='extremized_logit_mean' else [dict(lam=l,k=k) for l,k in itertools.product(LAM,K)] if method.startswith('perf') else [{}]
            def predict(params):
                if method=='mean': return probabilities.mean(axis=1)
                if method=='median': return np.median(probabilities,axis=1)
                if method=='extremized_logit_mean': return expit(params['a']*logit(np.clip(probabilities,.01,.99)).mean(axis=1))
                if method.startswith('best'): return probabilities[np.arange(len(rows)),np.argmin(scores,axis=1)]
                k=params['k']
                shrunk=sizes/(sizes+k)*scores+k/(sizes+k)*population
                return (softmax(-params['lam']*shrunk,axis=1)*probabilities).sum(axis=1)
            losses=[np.mean((predict(p)[~test_mask]-outcomes[~test_mask])**2) if (~test_mask).any() else np.inf for p in grid]
            params=grid[int(np.argmin(losses))]
            choices.append(dict(fold=fold,method=method,minimum=minimum,train_panels=int((~test_mask).sum()),test_ids=list(test),**params))
            predicted=predict(params)
            for idx in np.flatnonzero(test_mask):
                q,draw,_,_=rows[idx]
                predictions.append(dict(question_id=q,draw=draw,fold=fold,method=method,prediction=predicted[idx],outcome=outcomes[idx],brier=(predicted[idx]-outcomes[idx])**2))
    return pd.DataFrame(predictions),choices
