"""Synthetic Iowa cash-donation counterexample; no population data.

Run with the pinned environment at
/Users/maxghenis/charitable-donation-counterexamples/.venv/bin/python.
All dollar results below are complete calculate_household runs.
"""

import importlib.metadata as md
import json
from pathlib import Path

import policyengine as pe

YEAR = 2026
WAGES = 114_150
GIFT = 10
EXTRAS = [
    "adjusted_gross_income",
    "taxable_income",
    "taxable_income_deductions",
    "standard_deduction",
    "tax_unit_itemizes",
    "charitable_deduction_for_non_itemizers",
    "charitable_deduction",
    "ia_taxable_income_consolidated",
    "ia_cdcc",
    "cdcc_potential",
    "cdcc",
    "tax_unit_childcare_expenses",
    "income_tax",
    "state_income_tax",
    "household_benefits",
    "household_tax",
    "household_refundable_tax_credits",
    "child_care_subsidies",
]


def run(gift):
    return pe.us.calculate_household(
        people=[
            {
                "age": 40,
                "employment_income": WAGES,
                "charitable_cash_donations": gift,
            },
            {"age": 8},
        ],
        marital_unit=[{"members": [0]}, {"members": [1]}],
        tax_unit={"filing_status": "HEAD_OF_HOUSEHOLD"},
        spm_unit={"spm_unit_pre_subsidy_childcare_expenses": 3_000},
        household={"state_code": "IA", "county_fips": "19153"},
        year=YEAR,
        extra_variables=EXTRAS,
    )


def summarize(result, gift):
    t = result.tax_unit
    h = result.household
    s = result.spm_unit
    return {
        "gift": gift,
        "wages": WAGES,
        "adjusted_gross_income": t.adjusted_gross_income,
        "taxable_income": t.taxable_income,
        "taxable_income_deductions": t.taxable_income_deductions,
        "standard_deduction": t.standard_deduction,
        "tax_unit_itemizes": t.tax_unit_itemizes,
        "charitable_deduction_for_non_itemizers": t.charitable_deduction_for_non_itemizers,
        "charitable_deduction": t.charitable_deduction,
        "ia_taxable_income_consolidated": t.ia_taxable_income_consolidated,
        "ia_cdcc": t.ia_cdcc,
        "cdcc_potential": t.cdcc_potential,
        "cdcc": t.cdcc,
        "tax_unit_childcare_expenses": t.tax_unit_childcare_expenses,
        "income_tax": t.income_tax,
        "state_income_tax": t.state_income_tax,
        "household_benefits": h.household_benefits,
        "household_tax": h.household_tax,
        "household_refundable_tax_credits": h.household_refundable_tax_credits,
        "child_care_subsidies": s.child_care_subsidies,
        "household_net_income": h.household_net_income,
        "after_gift_resources": h.household_net_income - gift,
    }


if __name__ == "__main__":
    baseline = summarize(run(0), 0)
    donation = summarize(run(GIFT), GIFT)
    report = {
        "hypothetical_household": True,
        "year": YEAR,
        "versions": {p: md.version(p) for p in ("policyengine", "policyengine-us")},
        "assumptions": [
            "Iowa resident, single parent age40, dependent age8, qualifying HOH filing status",
            "Employment wages114150, no other income or deductions",
            "3000 of unreimbursed employment-related qualifying childcare expenses",
            "10 cash donation to eligible public charity, no goods/services or state credit",
            "No itemization before or after donation",
        ],
        "baseline": baseline,
        "donation": donation,
        "net_resource_gain_after_gift": donation["after_gift_resources"]
        - baseline["after_gift_resources"],
        "federal_income_tax_saving": baseline["income_tax"] - donation["income_tax"],
        "state_income_tax_saving": baseline["state_income_tax"]
        - donation["state_income_tax"],
        "sources": [
            "https://revenue.iowa.gov/taxes/tax-guidance/individual-income-tax/1040-expanded-instructions/child-dependent-care-credit",
            "https://www.irs.gov/taxtopics/tc506",
        ],
    }
    print(json.dumps(report, indent=2))
    Path(__file__).with_suffix(".json").write_text(json.dumps(report, indent=2) + "\n")
    assert not baseline["tax_unit_itemizes"] and not donation["tax_unit_itemizes"]
    assert baseline["adjusted_gross_income"] == donation["adjusted_gross_income"]
    assert report["net_resource_gain_after_gift"] > 0
