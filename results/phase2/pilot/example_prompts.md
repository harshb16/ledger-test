## 1286/MIX/0/C1

You are aggregating probability forecasts. Five forecasters (A-E) each gave a probability that the same binary target question resolves YES. The question text is deliberately withheld: you see only an anonymised category code and the time horizon. All five forecasts were made at the same time. If track records are shown, they describe each forecaster on past resolved questions that are different from the target. Report the probability for the target that minimises expected Brier score, and the non-negative relative weight you effectively gave each forecaster. Respond with JSON only, no rationale.

Target question: category OD, horizon 91–180d.
Current forecasts (probability of YES):
A: 0.020
C: 0.000
B: 0.030
E: 0.150
D: 0.150

Track records:
A:
category AX, horizon 91–180d: forecast 0.030, resolved NO
category AX, horizon 91–180d: forecast 0.990, resolved YES
category AX, horizon 8–30d: forecast 1.000, resolved YES
category AW, horizon 91–180d: forecast 0.010, resolved NO
category JF, horizon 91–180d: forecast 0.920, resolved YES
category MI, horizon 91–180d: forecast 0.500, resolved YES
category MI, horizon ≤7d: forecast 0.500, resolved YES
category AW, horizon >365d: forecast 0.040, resolved NO

C:
category AX, horizon 181–365d: forecast 0.950, resolved YES
category JF, horizon ≤7d: forecast 0.010, resolved NO
category AX, horizon 91–180d: forecast 0.000, resolved NO
category MI, horizon 31–90d: forecast 0.510, resolved YES
category UP, horizon ≤7d: forecast 0.000, resolved NO
category JF, horizon 8–30d: forecast 0.760, resolved YES
category IV, horizon ≤7d: forecast 0.480, resolved NO
category UP, horizon ≤7d: forecast 0.000, resolved NO

B:
category DS, horizon 8–30d: forecast 1.000, resolved YES
category YX, horizon 8–30d: forecast 0.500, resolved NO
category UP, horizon 8–30d: forecast 0.000, resolved NO
category AX, horizon 91–180d: forecast 0.100, resolved YES
category IV, horizon 181–365d: forecast 0.800, resolved NO
category DS, horizon 181–365d: forecast 0.600, resolved YES
category AX, horizon 91–180d: forecast 0.800, resolved NO
category OD, horizon 181–365d: forecast 0.800, resolved NO

E:
category IV, horizon 31–90d: forecast 0.300, resolved NO
category YX, horizon 181–365d: forecast 0.000, resolved NO
category IV, horizon 31–90d: forecast 0.500, resolved NO
category YX, horizon 91–180d: forecast 0.800, resolved NO
category MI, horizon 8–30d: forecast 0.500, resolved YES
category AX, horizon 91–180d: forecast 0.200, resolved NO
category AW, horizon ≤7d: forecast 0.800, resolved YES
category UP, horizon 181–365d: forecast 0.400, resolved YES

D:
category IV, horizon 8–30d: forecast 0.500, resolved YES
category IV, horizon 91–180d: forecast 0.400, resolved NO
category UP, horizon ≤7d: forecast 0.100, resolved NO
category DS, horizon ≤7d: forecast 0.800, resolved NO
category IV, horizon 181–365d: forecast 0.600, resolved NO
category JF, horizon 91–180d: forecast 0.070, resolved NO
category DS, horizon 91–180d: forecast 0.050, resolved NO
category YX, horizon 181–365d: forecast 0.010, resolved NO

## 1286/PUB/0/C3_farmed

You are aggregating probability forecasts. Five forecasters (A-E) each gave a probability that the same binary target question resolves YES. The question text is deliberately withheld: you see only an anonymised category code and the time horizon. All five forecasts were made at the same time. If track records are shown, they describe each forecaster on past resolved questions that are different from the target. Report the probability for the target that minimises expected Brier score, and the non-negative relative weight you effectively gave each forecaster. Respond with JSON only, no rationale.

Target question: category OD, horizon 91–180d.
Current forecasts (probability of YES):
C: 0.900
E: 1.000
D: 0.030
A: 0.030
B: 0.300

Track records:
C:
Relative Brier vs other forecasters on the same 8 questions: +0.056 (negative = better than peers, 0 = typical)

E:
Relative Brier vs other forecasters on the same 8 questions: +0.048 (negative = better than peers, 0 = typical)

D:
Relative Brier vs other forecasters on the same 8 questions: +0.211 (negative = better than peers, 0 = typical)

A:
Relative Brier vs other forecasters on the same 8 questions: +0.058 (negative = better than peers, 0 = typical)

B:
Relative Brier vs other forecasters on the same 8 questions: +0.018 (negative = better than peers, 0 = typical)