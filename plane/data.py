import pandas as pd


def load_sessions(path: str, multiplier_col: str, session_col: str | None = None) -> pd.DataFrame:
    if path.lower().endswith(".csv"):
        df = pd.read_csv(path)
    elif path.lower().endswith(".json"):
        df = pd.read_json(path)
    else:
        raise ValueError("Unsupported file format; use CSV or JSON")

    if multiplier_col not in df.columns:
        raise ValueError(f"Missing multiplier column '{multiplier_col}'")

    m = pd.to_numeric(df[multiplier_col], errors="coerce")
    if (m < 1).any():
        raise ValueError("All multipliers must be >= 1")

    out = pd.DataFrame({"multiplier": m})
    if session_col and session_col in df.columns:
        out["session_id"] = df[session_col]
    else:
        out["session_id"] = 0

    out = out.dropna().reset_index(drop=True)
    return out
