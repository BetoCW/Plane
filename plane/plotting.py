import matplotlib.pyplot as plt
import numpy as np


def plot_survival(emp, fits):
    t = emp["t"]
    S = emp["S"]
    plt.figure(figsize=(7,5))
    plt.step(t, S, where='post', label='Empirical S(x)')
    grid_t = np.linspace(1, t.max(), 300)
    for f in fits:
        plt.plot(grid_t, f["survival"](grid_t), label=f["name"])
    plt.yscale('log')
    plt.xlabel('x')
    plt.ylabel('S(x)=P(X>=x)')
    plt.title('Survival Function (log scale)')
    plt.legend()
    plt.tight_layout()
    plt.show()
