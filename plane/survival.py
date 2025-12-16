import numpy as np


def empirical_survival(x: np.ndarray):
    x = np.asarray(x)
    x = x[~np.isnan(x)]
    x = x[x >= 1]
    x_sorted = np.sort(x)
    n = x_sorted.size
    # S(t) at unique t values
    uniq = np.unique(x_sorted)
    S = []
    for t in uniq:
        S.append(np.sum(x_sorted >= t) / n)
    return {"t": uniq, "S": np.array(S), "n": n}
