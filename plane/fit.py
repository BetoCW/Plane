import numpy as np
from scipy import stats


def fit_exponential(x):
    # Support x>=1; model X = 1 + Y where Y ~ Exp(lambda)
    y = np.asarray(x) - 1.0
    y = y[y >= 0]
    lam = 1.0 / (np.mean(y) + 1e-12)
    # log-likelihood for shifted exponential
    ll = np.sum(stats.expon(scale=1/lam).logpdf(y))
    aic = 2*1 - 2*ll
    return {"name": "exponential_shift1", "params": {"lambda": lam}, "ll": ll, "aic": aic,
            "survival": lambda t: np.exp(-lam * np.maximum(t-1, 0)),
            "rng": lambda: (lambda size=None: 1 + np.random.exponential(scale=1/lam, size=size))}


def fit_pareto(x):
    # Standard Pareto with xm=1, tail S(t) = (1/t)^alpha for t>=1
    z = np.asarray(x)
    z = z[z >= 1]
    # MLE for alpha with xm=1: alpha_hat = n / sum(log(z))
    alpha = z.size / np.sum(np.log(z))
    # log-likelihood for xm=1
    ll = np.sum(stats.pareto(b=alpha, scale=1).logpdf(z))
    aic = 2*1 - 2*ll
    return {"name": "pareto_xm1", "params": {"alpha": alpha}, "ll": ll, "aic": aic,
            "survival": lambda t: (np.where(t>=1, t**(-alpha), 1.0)),
            "rng": lambda: (lambda size=None: stats.pareto(b=alpha, scale=1).rvs(size=size))}


def fit_trunc_exp(x):
    # Truncated exponential tail beyond 1 with upper soft truncation via mixture
    # Simple 2-parameter: lambda and p for mixture of Exp and point mass near tail cap L
    z = np.asarray(x)
    z = z[z >= 1]
    y = z - 1
    lam = 1.0 / (np.mean(y) + 1e-12)
    # Estimate p as fraction of extreme events beyond quantile q
    q = np.quantile(z, 0.99) if z.size > 50 else np.max(z)
    p = np.mean(z >= q) * 0.5
    def survival(t):
        t = np.asarray(t)
        base = np.exp(-lam * np.maximum(t-1, 0))
        cap = np.where(t<=q, 1.0, np.exp(- (t - q)))
        return (1-p)*base + p*cap
    # pseudo log-likelihood using base model
    ll = np.sum(stats.expon(scale=1/lam).logpdf(y))
    aic = 2*2 - 2*ll
    return {"name": "truncated_exponential_mixture", "params": {"lambda": lam, "p": p, "q": float(q)}, "ll": ll, "aic": aic,
            "survival": survival,
            "rng": lambda: (lambda size=None: 1 + np.random.exponential(scale=1/lam, size=size))}


def fit_models(x):
    return [fit_exponential(x), fit_pareto(x), fit_trunc_exp(x)]


def best_model_by_aic(fits):
    return sorted(fits, key=lambda d: d["aic"])[0]
