"""Replay unusual records in a closed, managed household cohort.

Outputs contain record-level values and therefore stay ignored. The replay
enumerates tax-unit itemization choices within each selected household.
"""

import gc
import json
from pathlib import Path

import policyengine as pe
from policyengine.core.scoping_strategy import RowFilterStrategy

from inspect_population import read_pickle
from population_search import log

EXTRAS = [
    "household_id",
    "household_net_income",
    "household_tax",
    "household_benefits",
    "charitable_cash_donations",
    "income_tax",
    "state_income_tax",
    "taxable_income",
    "tax_unit_itemizes",
    "charitable_deduction_for_non_itemizers",
    "charitable_deduction",
    "cdcc",
    "cdcc_potential",
    "ks_cdcc",
    "nj_cdcc",
    "ok_child_care_child_tax_credit",
    "me_child_care_credit",
    "la_refundable_cdcc",
    "la_non_refundable_cdcc",
    "ga_itemizer_credit_potential",
    "ia_cdcc",
    "dc_kccatc",
    "md_deductions",
    "md_standard_deduction",
    "md_itemized_deductions",
    "md_taxable_income",
    "md_income_tax",
    "md_local_income_tax_before_credits",
    "va_deductions",
    "va_standard_deduction",
    "va_itemized_deductions",
    "va_taxable_income",
    "va_income_tax",
    "tax_liability_if_itemizing",
    "tax_liability_if_not_itemizing",
]


def snapshot(sim):
    return {
        name: sim.calc(name, period=2026, map_to="household")
        for name in EXTRAS
        if name in sim.tax_benefit_system.variables
    }


def main():
    private = Path("private_outputs")
    ids = read_pickle(private / "household_ids.pkl")
    selected = set()
    scenarios = []
    for path in sorted(private.glob("ordinary_cash_gift_[0-9]*.pkl")):
        if path.stem.endswith("_candidates"):
            continue
        amount = float(path.stem.removeprefix("ordinary_cash_gift_"))
        if amount == 0:
            continue
        result = read_pickle(path)
        candidates = (result["net_gain"] > result["numerical_tolerance"]) & (
            result["added_gift"] > 0
        )
        for value in ids[candidates]:
            selected.add(int(value))
        # Include records where the smallest gift increased state tax.
        if amount == 1:
            for value in ids[result["delta"]["household_tax"] > 0.02]:
                selected.add(int(value))
        scenarios.append(amount)
    if not selected:
        log("No records selected for replay")
        return
    log(f"Replaying {len(selected)} households")
    base = pe.us.managed_microsimulation(
        scoping_strategy=RowFilterStrategy(
            variable_name="household_id", variable_value=sorted(selected)
        )
    )
    household_ids = base.calc("household_id", period=2026)
    base_out = snapshot(base)
    national = read_pickle(private / "baseline.pkl")
    national_positions = {int(value): position for position, value in enumerate(ids)}
    for name in ("household_net_income", "household_tax", "household_benefits"):
        for index, household_id in enumerate(household_ids):
            expected = float(national[name].iloc[national_positions[int(household_id)]])
            observed = float(base_out[name].iloc[index])
            assert abs(observed - expected) <= abs(expected) * 1e-6 + 0.02, (
                name,
                int(household_id),
                observed,
                expected,
            )
    cash = base.calc("charitable_cash_donations", period=2026)
    heads = base.calc("is_tax_unit_head", period=2026)
    units = base.calc("tax_unit_id", period=2026)
    person_units = base.calc("tax_unit_id", period=2026, map_to="person")
    person_households = base.calc("household_id", period=2026, map_to="person")
    # Only structural ID memberships are handled here; monetary quantities
    # and weights continue to use the engine's entity mapping.
    unit_household = {}
    for unit_id, household_id in zip(person_units, person_households):
        previous = unit_household.setdefault(int(unit_id), int(household_id))
        assert previous == int(household_id)
    household_units = {}
    unit_rank = {}
    for unit_id in units:
        group = household_units.setdefault(unit_household[int(unit_id)], [])
        unit_rank[int(unit_id)] = len(group)
        group.append(int(unit_id))
    max_units = max(len(group) for group in household_units.values())
    assert max_units <= 6, "Split a cohort with many tax units into smaller replays"
    ranks = units.map(unit_rank)
    modes = ["automatic", *range(2**max_units)]
    filing_status = base.calc("filing_status", period=2026)
    unit_context = [
        {
            "household_id": unit_household[int(unit_id)],
            "tax_unit_id": int(unit_id),
            "rank": unit_rank[int(unit_id)],
            "filing_status": str(filing_status.iloc[index]),
        }
        for index, unit_id in enumerate(units)
    ]
    (private / "replay_unit_context.json").write_text(
        json.dumps(unit_context, indent=2) + "\n"
    )
    result_rows = []
    for amount in [0, *scenarios]:
        for mode in modes:
            name = f"replay_{amount:g}_{mode}"
            branch = base.get_branch(name)
            branch.set_input("charitable_cash_donations", 2026, cash + heads * amount)
            if mode != "automatic":
                branch.set_input(
                    "tax_unit_itemizes",
                    2026,
                    ranks.map(lambda rank, mode=mode: (mode >> int(rank)) & 1),
                )
            branch.drop_computed_arrays()
            out = snapshot(branch)
            for index, household_id in enumerate(household_ids):
                added_gift = (
                    out["charitable_cash_donations"].iloc[index]
                    - base_out["charitable_cash_donations"].iloc[index]
                )
                result_rows.append(
                    {
                        "household_id": int(household_id),
                        "gift_per_tax_unit": amount,
                        "mode": mode,
                        "actual_added_gift": float(added_gift),
                        "net_income_after_gift": float(
                            out["household_net_income"].iloc[index] - added_gift
                        ),
                        "change_in_net_income_after_gift": float(
                            out["household_net_income"].iloc[index]
                            - base_out["household_net_income"].iloc[index]
                            - added_gift
                        ),
                        "outputs": {
                            key: float(series.iloc[index])
                            for key, series in out.items()
                        },
                    }
                )
            base.branches.pop(name)
            del branch, out
            gc.collect()
            log(f"Finished {name}")
    # Compare each household's best baseline and donation configurations,
    # including mixed elections in households containing multiple tax units.
    best_resources = {}
    for row in result_rows:
        key = (row["household_id"], row["gift_per_tax_unit"])
        best_resources[key] = max(
            best_resources.get(key, float("-inf")), row["net_income_after_gift"]
        )
    for row in result_rows:
        key = (row["household_id"], row["gift_per_tax_unit"])
        row["gain_comparing_best_filing_configuration"] = (
            best_resources[key] - best_resources[(row["household_id"], 0)]
        )
    (private / "candidate_replays.json").write_text(
        json.dumps(result_rows, indent=2) + "\n"
    )
    log("Replay completed")


if __name__ == "__main__":
    main()
