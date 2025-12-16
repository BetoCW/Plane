import os
import json
import pandas as pd
from typing import List


def append_values(path: str, values: List[float], session_id: str = "manual") -> int:
    vals = [v for v in values if v >= 1]
    if path.lower().endswith('.csv'):
        df_new = pd.DataFrame({"session_id": session_id, "multiplier": vals})
        try:
            df_old = pd.read_csv(path)
            df_out = pd.concat([df_old, df_new], ignore_index=True)
        except FileNotFoundError:
            df_out = df_new
        df_out.to_csv(path, index=False)
    elif path.lower().endswith('.json'):
        recs_new = [{"session_id": session_id, "multiplier": float(v)} for v in vals]
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, list):
                data.extend(recs_new)
            else:
                # store under key 'records'
                data = (data.get('records') or []) + recs_new
        except FileNotFoundError:
            data = recs_new
        # Normalize to list at top-level
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f)
    else:
        raise ValueError('Unsupported output format; use CSV or JSON')
    return len(vals)


def merge_files(inputs: List[str], out: str) -> None:
    rows = []
    for p in inputs:
        if p.lower().endswith('.csv'):
            df = pd.read_csv(p)
            if 'multiplier' not in df.columns:
                raise ValueError(f"Missing 'multiplier' in {p}")
            if 'session_id' not in df.columns:
                df['session_id'] = os.path.basename(p)
            rows.append(df[['session_id','multiplier']])
        elif p.lower().endswith('.json'):
            with open(p, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, list):
                recs = data
            else:
                recs = data.get('records', [])
            df = pd.DataFrame(recs)
            if 'multiplier' not in df.columns:
                raise ValueError(f"Missing 'multiplier' in {p}")
            if 'session_id' not in df.columns:
                df['session_id'] = os.path.basename(p)
            rows.append(df[['session_id','multiplier']])
        else:
            raise ValueError(f'Unsupported input file: {p}')
    df_all = pd.concat(rows, ignore_index=True)
    # Write output
    if out.lower().endswith('.csv'):
        df_all.to_csv(out, index=False)
    elif out.lower().endswith('.json'):
        recs = df_all.to_dict(orient='records')
        with open(out, 'w', encoding='utf-8') as f:
            json.dump(recs, f)
    else:
        raise ValueError('Unsupported output format; use CSV or JSON')
