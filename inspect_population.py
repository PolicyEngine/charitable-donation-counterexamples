"""Inspect population candidates without publishing record-level data."""

import json
import pickle
from pathlib import Path

import pandas as pd
import us


def read_pickle(path):
    with path.open("rb") as handle:
        return pickle.load(handle)


def main():
    private = Path("private_outputs")
    ids = read_pickle(private / "household_ids.pkl")
    # Geography is an input label only. Aggregates below remain MicroSeries
    # operations; no raw survey weights are fetched or reconstructed.
    households = pd.read_hdf("data/populace_us_2024.h5", "household")
    fips_by_id = households.set_index("household_id")["state_fips"]
    states = ids.map(fips_by_id).map(
        lambda code: us.states.lookup(str(int(code)).zfill(2)).abbr
    )
    reports = []
    for path in sorted(private.glob("ordinary_cash_gift_[0-9]*.pkl")):
        if path.stem.endswith("_candidates"):
            continue
        amount = float(path.stem.removeprefix("ordinary_cash_gift_"))
        result = read_pickle(path)
        gain = result["net_gain"]
        tolerance = result["numerical_tolerance"]
        candidate = (gain > tolerance) & (result["added_gift"] > 0)
        counts = {}
        for state in states[candidate].unique():
            keep = candidate & (states == state)
            counts[state] = {
                "raw_records": len(gain[keep]),
                "weighted_households": float(keep.sum()),
                "maximum_net_gain": float(gain[keep].max()),
            }
        report = {
            "additional_gift_per_tax_unit": amount,
            "unverified_candidate_counts_by_state": counts,
            "mean_added_gift_per_household": float(result["added_gift"].mean()),
            "mean_household_tax_reduction": float(
                (-result["delta"]["household_tax"]).mean()
            ),
            "mean_net_income_change_after_gift": float(gain.mean()),
            "tax_reduction_share_of_added_gifts": float(
                (-result["delta"]["household_tax"]).sum() / result["added_gift"].sum()
            )
            if amount
            else None,
            "maximum_cash_benefit_change": float(
                result["delta"]["household_benefits"].abs().max()
            ),
            "maximum_aca_credit_change": float(result["delta"]["aca_ptc"].abs().max()),
        }
        reports.append(report)
        # All record IDs and cell values stay in the ignored directory.
        rows = []
        for index in gain[candidate].sort_values(ascending=False).head(30).index:
            rows.append(
                {
                    "household_id": int(ids.loc[index]),
                    "record_index": int(index),
                    "state": states.loc[index],
                    "additional_gift": float(result["added_gift"].loc[index]),
                    "net_gain": float(gain.loc[index]),
                    "delta": {
                        key: float(series.loc[index])
                        for key, series in result["delta"].items()
                    },
                    "after": {
                        key: float(series.loc[index])
                        for key, series in result["out"].items()
                    },
                }
            )
        (private / f"{path.stem}_inspection.json").write_text(
            json.dumps(rows, indent=2) + "\n"
        )
    Path("population_inspection_summary.json").write_text(
        json.dumps(reports, indent=2) + "\n"
    )
    print(json.dumps(reports, indent=2))


if __name__ == "__main__":
    main()
