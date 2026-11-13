"""Search certified Microcosm US households for donation interactions.

Record-level results stay under ignored private_outputs/. All aggregates use
MicroSeries statistics, and entity transfers use the model's map_to machinery.
Run through ~/reviews/us-hub/scripts/heavy_run.sh on Max's machine.
"""

import argparse
import gc
import importlib.metadata as md
import json
import pickle
from pathlib import Path
import time

import policyengine as pe


CORE_OUTPUTS = [
    "household_net_income",
    "household_tax",
    "household_benefits",
    "household_market_income",
    "household_health_costs",
    "income_tax",
    "state_income_tax",
    "employee_payroll_tax",
    "charitable_cash_donations",
    "charitable_deduction",
    "charitable_deduction_for_non_itemizers",
    "adjusted_gross_income",
    "taxable_income",
    "dc_kccatc",
    "ia_cdcc",
    "tax_unit_itemizes",
    "standard_deduction",
    "itemized_taxable_income_deductions",
    "dc_taxable_income_joint",
    "dc_deduction_joint",
    "ia_taxable_income_consolidated",
    "dc_itemized_deductions",
    "cdcc_potential",
    "ga_itemizer_credit_potential",
    "ar_additional_tax_credit_for_qualified_individuals_person",
    "snap",
    "tanf",
    "ssi",
    "housing_assistance",
    "aca_ptc",
]


def log(message):
    print(f"[{time.strftime('%H:%M:%S')}] {message}", flush=True)


def snapshot(sim, year):
    results = {}
    for name in CORE_OUTPUTS:
        if name in sim.tax_benefit_system.variables:
            log(f"calculating {sim.branch_name}: {name}")
            results[name] = sim.calc(name, period=year, map_to="household")
    return results


def save_pickle(path, value):
    with path.open("wb") as handle:
        pickle.dump(value, handle, protocol=pickle.HIGHEST_PROTOCOL)


def search(amounts, year, reuse_baseline=False):
    private = Path("private_outputs")
    private.mkdir(exist_ok=True)
    log("loading certified default US dataset")
    base = pe.us.managed_microsimulation()
    if reuse_baseline:
        assert len(amounts) == 1, "Run each independent scenario in its own process"
        with (private / "provenance.pkl").open("rb") as handle:
            previous = pickle.load(handle)
        for key in ("bundle_id", "runtime_dataset_sha256"):
            assert previous[key] == base.policyengine_bundle[key]
    else:
        save_pickle(private / "provenance.pkl", base.policyengine_bundle)
    log(f"bundle: {json.dumps(base.policyengine_bundle, default=str)}")
    heads = base.calc("is_tax_unit_head", period=year)
    heads_per_unit = base.calc("is_tax_unit_head", period=year, map_to="tax_unit")
    assert ((heads_per_unit == 0) | (heads_per_unit == 1)).all(), (
        "At most one donor per tax unit"
    )
    no_head_units = len(heads_per_unit[heads_per_unit == 0])
    log(f"tax units without an adult head (not given a gift): {no_head_units}")
    original_cash = base.calc("charitable_cash_donations", period=year)
    cash_by_household = base.calc(
        "charitable_cash_donations", period=year, map_to="household"
    )
    donors_per_household = base.calc(
        "is_tax_unit_head", period=year, map_to="household"
    )
    household_ids = base.calc("household_id", period=year)
    person_households = base.calc("household_id", period=year, map_to="person")
    log(
        f"input rows: {len(household_ids)} households, {len(heads_per_unit)} tax units, {len(heads)} people"
    )

    if reuse_baseline:
        with (private / "baseline.pkl").open("rb") as handle:
            baseline = pickle.load(handle)
        with (private / "household_ids.pkl").open("rb") as handle:
            assert household_ids.equals(pickle.load(handle))
        assert baseline["charitable_cash_donations"].equals(cash_by_household)
    else:
        baseline = snapshot(base, year)
        save_pickle(private / "baseline.pkl", baseline)
        save_pickle(private / "household_ids.pkl", household_ids)
        save_pickle(private / "person_households.pkl", person_households)
    assert baseline["household_net_income"].notna().all()
    public = {
        "year": year,
        "versions": {
            p: md.version(p)
            for p in ("policyengine", "policyengine-us", "policyengine-core")
        },
        "provenance": base.policyengine_bundle,
        "raw_household_records": len(household_ids),
        "raw_tax_unit_records": len(heads_per_unit),
        "raw_tax_unit_records_without_a_head": no_head_units,
        "design": "Add gift to each model tax-unit head on top of baseline cash gifts; child-only units without a head receive no added gift; no special state donation credit inputs.",
        "candidate_status": "Unverified screen; individual reruns and source checks required before interpreting as real tax-law exceptions.",
        "scenarios": [],
    }
    if reuse_baseline and Path("population_summary.json").exists():
        public = json.loads(Path("population_summary.json").read_text())
        assert public["year"] == year
    if not amounts:
        Path("population_summary.json").write_text(json.dumps(public, indent=2) + "\n")
    for amount in amounts:
        log(f"starting additional gift ${amount:g} per tax unit")
        name = f"ordinary_cash_gift_{amount:g}"
        # A fresh input-only managed simulation avoids retaining two complete
        # population calculation caches in RAM. Branches remain supported for
        # a caller deliberately running a small bounded cohort in one process.
        scenario = base if reuse_baseline else base.get_branch(name)
        scenario.set_input(
            "charitable_cash_donations", year, original_cash + heads * amount
        )
        # Explicitly invalidate derived values; source data and declared inputs remain.
        scenario.drop_computed_arrays()
        assert scenario.calc("household_id", period=year).equals(household_ids)
        intended_cash = original_cash + heads * amount
        stored_cash = scenario.calc("charitable_cash_donations", period=year)
        input_tolerance = original_cash.abs() * 2e-7 + 0.001
        assert ((stored_cash - intended_cash).abs() <= input_tolerance).all()
        out = snapshot(scenario, year)
        delta = {key: out[key] - baseline[key] for key in baseline}
        added_gift = out["charitable_cash_donations"] - cash_by_household
        gift_tolerance = cash_by_household.abs() * 2e-7 + 0.02
        assert (
            (added_gift - donors_per_household * amount).abs() <= gift_tolerance
        ).all()
        assert delta["household_market_income"].abs().max() <= 0.01
        # Cash identity permits changed health costs, which net income includes.
        identity_error = (
            delta["household_net_income"]
            + delta["household_tax"]
            - delta["household_benefits"]
            + delta["household_health_costs"]
        )
        net_gain = delta["household_net_income"] - added_gift
        tax_saving = -delta["household_tax"]
        benefit_gain = delta["household_benefits"]
        assert net_gain.notna().all() and tax_saving.notna().all()
        if amount == 0:
            for key, change in delta.items():
                assert change.abs().max() <= 0.02, f"Zero-gift control changed {key}"
        # Float32 model monetary arrays can jump several dollars at very high
        # incomes. Screen conservatively, then reproduce candidate households.
        tolerance = (
            baseline["household_net_income"].abs()
            + out["household_net_income"].abs()
            + baseline["household_tax"].abs()
            + out["household_tax"].abs()
        ) * 2e-7 + 0.02
        assert (identity_error.abs() <= tolerance).all(), (
            "Household cash accounting failed"
        )
        mask = (net_gain > tolerance) & (added_gift > 0)
        tax_exceeds = tax_saving > added_gift + tolerance
        row = {
            "additional_gift_per_tax_unit": amount,
            "raw_household_records_better_off": len(net_gain[mask]),
            "weighted_households_better_off": float(mask.sum()),
            "weighted_household_share_better_off": float(mask.mean()),
            "raw_households_tax_saving_exceeds_gift": len(tax_saving[tax_exceeds]),
            "maximum_net_gain_after_gift": float(net_gain.max()),
            "maximum_tax_saving_per_dollar_given": float(
                (tax_saving[added_gift > 0] / added_gift[added_gift > 0]).max()
            )
            if amount
            else None,
            "raw_households_with_tax_increase": len(tax_saving[tax_saving < -0.02]),
            "raw_households_with_benefit_change": len(
                benefit_gain[benefit_gain.abs() > 0.02]
            ),
            "maximum_accounting_residual": float(identity_error.abs().max()),
        }
        save_pickle(
            private / f"{name}.pkl",
            {
                "delta": delta,
                "added_gift": added_gift,
                "net_gain": net_gain,
                "top_net_gain_indices": list(
                    net_gain.sort_values(ascending=False).head(20).index
                ),
                "out": out,
                "numerical_tolerance": tolerance,
            },
        )
        public["scenarios"] = [
            item
            for item in public["scenarios"]
            if item["additional_gift_per_tax_unit"] != amount
        ] + [row]
        Path("population_summary.json").write_text(
            json.dumps(public, indent=2, default=str) + "\n"
        )
        log(json.dumps(row))
        # Retain a list of suspicious household IDs only in the ignored output.
        save_pickle(
            private / f"{name}_candidates.pkl",
            {
                "better_off_ids": household_ids[mask],
                "top_ids": household_ids.loc[
                    net_gain.sort_values(ascending=False).head(20).index
                ],
            },
        )
        if not reuse_baseline:
            base.branches.pop(name)
        del scenario, out, delta, added_gift, net_gain, tax_saving, benefit_gain
        gc.collect()
    if not reuse_baseline:
        assert base.calc("charitable_cash_donations", period=year).equals(original_cash)
    log("all requested full scenarios completed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, default=2026)
    parser.add_argument("--reuse-baseline", action="store_true")
    parser.add_argument("--baseline-only", action="store_true")
    parser.add_argument(
        "--amounts", nargs="+", type=float, default=[0, 1, 10, 100, 1_000, 10_000]
    )
    args = parser.parse_args()
    search([] if args.baseline_only else args.amounts, args.year, args.reuse_baseline)
