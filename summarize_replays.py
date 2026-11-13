"""Publish only aggregate validation results from ignored record replays."""

import json
from pathlib import Path

from inspect_population import read_pickle


def main():
    private = Path("private_outputs")
    ids = read_pickle(private / "household_ids.pkl")
    rows = json.loads((private / "candidate_replays.json").read_text())
    automatic = {
        (r["household_id"], r["gift_per_tax_unit"]): r
        for r in rows
        if r["mode"] == "automatic"
    }
    contexts = json.loads((private / "replay_unit_context.json").read_text())
    candidates = []
    for amount in (1, 10, 100, 1000, 10000):
        original = read_pickle(private / f"ordinary_cash_gift_{amount}.pkl")
        mask = (original["net_gain"] > original["numerical_tolerance"]) & (
            original["added_gift"] > 0
        )
        for household_id in ids[mask]:
            candidates.append(automatic[(int(household_id), amount)])
    candidate_ids = {row["household_id"] for row in candidates}
    statuses = {
        row["filing_status"] for row in contexts if row["household_id"] in candidate_ids
    }
    assert "SEPARATE" not in statuses, (
        "Check spousal itemization constraints for separate filers"
    )
    gains = [r["gain_comparing_best_filing_configuration"] for r in candidates]
    assert all(value < 0 for value in gains)
    credit_names = [
        "ks_cdcc",
        "nj_cdcc",
        "ok_child_care_child_tax_credit",
        "me_child_care_credit",
        "la_refundable_cdcc",
        "la_non_refundable_cdcc",
    ]
    count_credit_increases = 0
    for (household_id, amount), row in automatic.items():
        if amount != 1:
            continue
        before = automatic[(household_id, 0)]["outputs"]
        after = row["outputs"]
        if after["household_tax"] - before["household_tax"] > 0.02:
            assert after["cdcc"] < before["cdcc"]
            assert any(
                after.get(name, 0) < before.get(name, 0) - 0.001
                for name in credit_names
            )
            count_credit_increases += 1
    result = {
        "year": 2026,
        "candidate_household_scenario_observations": len(candidates),
        "unique_candidate_households": len(candidate_ids),
        "candidate_filing_statuses": sorted(statuses),
        "candidate_observations_with_positive_gain_after_comparing_filing_choices": sum(
            value > 0 for value in gains
        ),
        "largest_after_gift_gain_among_candidates_after_filing_comparison": max(gains),
        "replayed_households": len({row["household_id"] for row in rows}),
        "itemization_configurations_including_automatic_per_amount": len(
            {row["mode"] for row in rows}
        ),
        "tested_amounts_in_replay": sorted({row["gift_per_tax_unit"] for row in rows}),
        "one_dollar_gift_tax_increase_records_confirmed_to_lose_childcare_credits": count_credit_increases,
        "interpretation": "All positive national-screen observations disappear when each household's baseline and donation filing choices are compared. The national screen does not prove no legal donation counterexample exists; the separate synthetic Iowa example demonstrates one.",
        "privacy": "No record identifiers or record-level input files are published.",
    }
    Path("population_validation_summary.json").write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
