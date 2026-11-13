"""Run hypothetical donation scenarios with the released PolicyEngine wrapper."""

import importlib.metadata as md
import json
from pathlib import Path

import policyengine as pe


def us_case(state: str, donation: float, *, qco: bool = False) -> dict:
    # A full state credit removes the gift's federal charitable deduction.
    # These two inputs therefore represent different statutory treatments.
    result = pe.us.calculate_household(
        people=[
            {
                "age": 40,
                "employment_income": 100_000,
                "charitable_cash_donations": 0 if qco else donation,
            }
        ],
        tax_unit={
            "filing_status": "SINGLE",
            **(
                {
                    "az_charitable_contributions_to_qualifying_charitable_organizations": donation
                }
                if qco
                else {}
            ),
        },
        household={
            "state_code": state,
            "county_fips": "04013" if state == "AZ" else "48201",
        },
        year=2026,
        extra_variables=[
            "income_tax",
            "state_income_tax",
            "charitable_deduction_for_non_itemizers",
            "az_charitable_contributions_credit",
            "household_tax",
        ],
    )
    return {
        "donation": donation,
        "federal_income_tax": result.tax_unit.income_tax,
        "state_income_tax": result.tax_unit.state_income_tax,
        "household_tax": result.household.household_tax,
        "az_charitable_credit": result.tax_unit.az_charitable_contributions_credit,
        "nonitemizer_deduction": result.tax_unit.charitable_deduction_for_non_itemizers,
        "net_income_before_gift": result.household.household_net_income,
        "net_income_after_gift": result.household.household_net_income - donation,
    }


def uk_savings_case(donation: float) -> dict:
    result = pe.uk.calculate_household(
        people=[
            {
                "age": 40,
                "employment_income": 49_271,
                "savings_interest_income": 1_000,
                "gift_aid": donation,
            }
        ],
        household={"region": "LONDON"},
        year=2026,
        extra_variables=[
            "income_tax",
            "savings_allowance",
            "savings_income_tax",
            "gift_aid_grossed_up",
            "net_income",
            "allowances",
            "adjusted_net_income",
        ],
    )
    person = result.person[0]
    return {
        "donation": donation,
        "income_tax": person.income_tax,
        "savings_allowance": person.savings_allowance,
        "savings_income_tax": person.savings_income_tax,
        "grossed_up_gift": person.gift_aid_grossed_up,
        "net_income": person.net_income,
        "allowances": person.allowances,
        "adjusted_net_income": person.adjusted_net_income,
    }


def main():
    results = {
        "versions": {
            p: md.version(p)
            for p in ["policyengine", "policyengine-us", "policyengine-uk"]
        },
        "year": 2026,
        "hypothetical_households": True,
        "texas_ordinary": [us_case("TX", d) for d in (0, 1_000)],
        "arizona_qco": [us_case("AZ", d, qco=True) for d in (0, 500)],
        "uk_savings": [uk_savings_case(d) for d in (0, 1)],
    }
    Path("results.json").write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
