# snapshot final=true t=2026-11-06T09:00:00Z

Coder pairs (amendment 26(j)), runs resolved per pair and their share, over the 2442 primary-scope run(s) the analysis selects, not this table's own runs: sol+opus 2042 (0.836); opus+sonnet 11 (0.0045)

| outcome | n | converged | note | scale_residual | var_model | var_region |
|---|---|---|---|---|---|---|
| omission | 1718 | True | Maximum Likelihood optimization failed to converge. Check mle_retvals; Retrying MixedLM optimization with lbfgs; The MLE may be on the boundary of the parameter space. | 0.08334 | 0.1094 | 0.0002915 |
| coverage_baseline | 1758 | False | Gradient optimization failed, |grad| = 4.440977; Maximum Likelihood optimization failed to converge. Check mle_retvals; MixedLM optimization failed, trying a different optimizer may help.; Retrying MixedLM optimization with cg; Retrying MixedLM optimization with lbfgs; The MLE may be on the boundary of the parameter space. | 0.03505 | 0.07039 | 9.59e-07 |
| coverage_target | 1758 | True | Maximum Likelihood optimization failed to converge. Check mle_retvals; Retrying MixedLM optimization with lbfgs; The MLE may be on the boundary of the parameter space. | 0.03731 | 0.06874 | 1.166e-06 |
| event_f1 | 1511 | False | Gradient optimization failed, |grad| = 20.843354; Maximum Likelihood optimization failed to converge. Check mle_retvals; MixedLM optimization failed, trying a different optimizer may help.; Retrying MixedLM optimization with cg; Retrying MixedLM optimization with lbfgs; The Hessian matrix at the estimated parameter values is not positive definite. | 0.01652 | 0.08235 | 0.02073 |
| tokens | 2092 | True | Maximum Likelihood optimization failed to converge. Check mle_retvals; Retrying MixedLM optimization with lbfgs; The MLE may be on the boundary of the parameter space. | 1.776 | 2.165 | 5.063e-05 |
| undisclosed | 1718 | True | Maximum Likelihood optimization failed to converge. Check mle_retvals; Random effects covariance is singular; Retrying MixedLM optimization with lbfgs; The MLE may be on the boundary of the parameter space. | 0.08326 | 0.08077 | 0.0002973 |
| end_to_end | 2092 | True | Maximum Likelihood optimization failed to converge. Check mle_retvals; Retrying MixedLM optimization with lbfgs; The MLE may be on the boundary of the parameter space. | 0.124 | 0.09792 | 5.536e-06 |
| false_alarm | 289 | True | The MLE may be on the boundary of the parameter space. | 0.0265 | 0.03644 | 0.0001871 |
