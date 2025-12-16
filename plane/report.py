import numpy as np


def summarize_fit(fits, best):
    lines = []
    lines.append("Model fits (lower AIC is better):")
    for f in sorted(fits, key=lambda d: d["aic"]):
        lines.append(f"- {f['name']}: AIC={f['aic']:.2f}, ll={f['ll']:.2f}, params={f['params']}")
    lines.append("")
    lines.append(f"Best: {best['name']} with params {best['params']}")
    return "\n".join(lines)


def prob_ge_thresholds(best, xs):
    xs = np.asarray(xs)
    S = best["survival"]
    return np.array([float(S(x)) for x in xs])
