"""P03 intake contract. No participant-level exclusion log is produced."""
import re
import numpy as np
import pandas as pd

ID = re.compile(r"p03-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\Z")


def flag(value):
    if isinstance(value, (bool, np.bool_)):
        return "true" if value else "false"
    if pd.isna(value):
        return "missing"
    if isinstance(value, str):
        if value in ("True", "true"):
            return "true"
        if value in ("False", "false"):
            return "false"
        if value in ("", "NA"):
            return "missing"
    return "invalid"


def read_records(path):
    # Prevent a malformed token from changing the interpretation of a whole
    # Boolean column. Preserve leading zeros and exact identifier spelling.
    return pd.read_csv(path, dtype={"study_id": "string", "consent": "string",
                                    "eligible": "string"},
                       keep_default_na=False, na_values=["", "NA"])


def select(raw):
    required = {"study_id", "consent", "eligible"}
    if not required <= set(raw):
        raise ValueError("Missing intake columns")
    c = raw.consent.map(flag)
    e = raw.eligible.map(flag)
    allowed = c.eq("true") & e.eq("true")
    valid_id = raw.study_id.map(lambda v: isinstance(v, str) and ID.fullmatch(v) is not None)
    if not valid_id[allowed].all():
        raise ValueError("Missing or invalid P03 study_id among consented eligible records")
    # Duplicates across even excluded records may indicate a contradictory
    # consent or repeated response. Stop rather than selecting a convenient row.
    if raw.loc[valid_id, "study_id"].duplicated().any():
        raise ValueError("Duplicate P03 study_id; adjudicate in restricted storage")
    flow = {"submitted":len(raw), "accepted":int(allowed.sum())}
    for status in ("false","missing","invalid"):
        flow["consent_"+status] = int(c.eq(status).sum())
        flow["eligibility_"+status] = int((c.eq("true") & e.eq(status)).sum())
    if sum(flow[k] for k in flow if k != "submitted") != len(raw):
        raise AssertionError("Intake flow inconsistent")
    data = raw.loc[allowed].copy()
    data["consent"] = True
    data["eligible"] = True
    data.attrs["intake_flow"] = flow
    return data
