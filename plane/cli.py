import argparse
from .data import load_sessions
from .survival import empirical_survival
from .fit import fit_models, best_model_by_aic
from .report import summarize_fit, prob_ge_thresholds
from .fair import sequence


def make_parser():
    p = argparse.ArgumentParser(
        description="Probabilistic reverse engineering of stochastic multipliers"
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    p_fit = sub.add_parser("fit", help="Fit candidate models to data")
    p_fit.add_argument("--data", required=True, help="Path to CSV/JSON data")
    p_fit.add_argument("--column", required=True, help="Column with multipliers (>=1)")
    p_fit.add_argument("--session", default=None, help="Optional session id column")
    p_fit.add_argument("--plot", action="store_true", help="Show survival plot")

    p_prob = sub.add_parser("prob", help="Compute P(X>=x) with best model")
    p_prob.add_argument("--data", required=True, help="Path to CSV/JSON data")
    p_prob.add_argument("--column", required=True)
    p_prob.add_argument("--session", default=None)
    p_prob.add_argument("--x", nargs="+", type=float, required=True, help="Thresholds")

    p_sim = sub.add_parser("simulate", help="Simulate rounds from best model")
    p_sim.add_argument("--data", required=True)
    p_sim.add_argument("--column", required=True)
    p_sim.add_argument("--session", default=None)
    p_sim.add_argument("--n", type=int, default=1000)

    # Manual data operations
    p_add = sub.add_parser("add", help="Append manually provided multipliers to a CSV/JSON")
    p_add.add_argument("--out", required=True, help="Destination CSV or JSON file")
    p_add.add_argument("--values", nargs="+", type=float, required=True, help="Multipliers to append (>=1)")
    p_add.add_argument("--session", default="manual", help="Session id label to store")

    p_merge = sub.add_parser("merge", help="Merge multiple CSV/JSON files into one")
    p_merge.add_argument("--inputs", nargs="+", required=True, help="Input file paths (CSV/JSON)")
    p_merge.add_argument("--out", required=True, help="Output CSV or JSON")

    p_pf = sub.add_parser("pf", help="Provably Fair: compute crash multipliers from seeds")
    p_pf.add_argument("--server", required=True, help="Server seed (string)")
    p_pf.add_argument("--client", required=True, help="Client seed (string)")
    p_pf.add_argument("--nonce", type=int, default=0, help="Starting nonce (default 0)")
    p_pf.add_argument("--rounds", type=int, default=1, help="Number of rounds to generate")
    p_pf.add_argument("--edge", type=float, default=0.99, help="House edge factor (default 0.99)")

    return p


def main(argv=None):
    parser = make_parser()
    args = parser.parse_args(argv)

    if args.cmd in {"fit", "prob", "simulate"}:
        df = load_sessions(args.data, multiplier_col=args.column, session_col=args.session)
        S = empirical_survival(df["multiplier"].values)
        fits = fit_models(df["multiplier"].values)
        best = best_model_by_aic(fits)

    if args.cmd == "fit":
        print(summarize_fit(fits, best))
        if getattr(args, "plot", False):
            from .plotting import plot_survival
            plot_survival(S, fits)
    elif args.cmd == "prob":
        probs = prob_ge_thresholds(best, args.x)
        for x, p in zip(args.x, probs):
            print(f"P(X>= {x:.4g}) = {p:.6f}")
    elif args.cmd == "simulate":
        rng = best["model"].rng()
        import numpy as np
        samples = rng(size=args.n)
        print("Simulated samples (first 20):", np.array2string(samples[:20], precision=4))
    elif args.cmd == "add":
        from .manual import append_values
        count = append_values(args.out, args.values, session_id=args.session)
        print(f"Appended {count} values to {args.out}.")
    elif args.cmd == "merge":
        from .manual import merge_files
        merge_files(args.inputs, args.out)
        print(f"Merged {len(args.inputs)} files into {args.out}.")
    elif args.cmd == "pf":
        vals = sequence(args.server, args.client, args.nonce, args.rounds, house_edge=args.edge)
        for i, v in enumerate(vals):
            print(f"nonce={args.nonce + i}  R={v:.4f}x")


if __name__ == "__main__":
    main()
