"""Development correlation-moment fit indices.

Trace-corrected excess discrepancy is a custom diagnostic, not validated
WLSMV robust CFI/TLI/RMSEA. Thresholds are unrestricted and fit exactly in
both target and independence models. No RMSEA interval or nested test.
"""
import numpy as np

def discrepancy_indices(statistic,df,baseline_statistic,baseline_df,n,
                        model_expected=None,baseline_expected=None):
    if (not all(np.isfinite(v) for v in (statistic,df,baseline_statistic,baseline_df,n))
        or min(statistic,baseline_statistic)<0 or not 0<df<baseline_df or n<=1):
        raise ValueError("invalid discrepancy inputs")
    corrected=model_expected is not None or baseline_expected is not None
    if corrected:
        if model_expected is None or baseline_expected is None:
            raise ValueError("both trace corrections required")
        if not all(np.isfinite(v) and v>0 for v in (model_expected,baseline_expected)):
            raise ValueError("invalid expected discrepancies")
    else:
        model_expected,baseline_expected=df,baseline_df
    # Excess discrepancy estimated in the original common DWLS metric.
    target=statistic-model_expected
    baseline=baseline_statistic-baseline_expected
    denominator=max(target,baseline,0.)
    cfi=1-max(target,0.)/denominator if denominator>1e-10 else None
    tli=1-(target/df)/(baseline/baseline_df) if baseline>1e-10 else None
    rmsea=np.sqrt(max(target,0.)/((n-1)*df))
    return {"label":"trace-corrected discrepancy diagnostics" if corrected else "uncorrected DWLS diagnostics",
            "cfi_like":float(cfi) if cfi is not None else None,
            "tli_like":float(tli) if tli is not None else None,
            "rmsea_like":float(rmsea),"target_excess":float(target),
            "baseline_excess":float(baseline),"nominal_df":int(df),
            "baseline_df":int(baseline_df),
            "validated_wlsmv":False}

def from_fit(fit):
    if not fit.fit.proper:
        raise ArithmeticError("improper fit")
    args=(fit.statistic,fit.nominal_df,fit.baseline_statistic,
          fit.baseline_df,fit.sample_size)
    return {"uncorrected":discrepancy_indices(*args),
            "trace_corrected":discrepancy_indices(*args,
                model_expected=fit.model_expected,baseline_expected=fit.baseline_expected),
            "polychoric_rms_residual":fit.fit.rms_residual,
            "moment_matched_p_value":fit.p_value,
            "effective_df":fit.effective_df}
