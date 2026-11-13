"""Fixed hypothetical Kansas household: ordinary cash gift can increase net tax.

Reproduce with policyengine[us]==6.19.0 (US model2.2.1), Python3.13.
Both results are full PolicyEngine household runs, without reforms or
computed-variable input overrides. Dollar amounts are model estimates.
"""

import importlib.metadata as md
import json
from pathlib import Path

import policyengine as pe

GIFT = 100
EXTRAS = [
    "adjusted_gross_income",
    "taxable_income",
    "tax_unit_itemizes",
    "charitable_deduction_for_non_itemizers",
    "income_tax_before_credits",
    "cdcc_potential",
    "cdcc_credit_limit",
    "cdcc",
    "ks_cdcc",
    "ks_income_tax_before_credits",
    "ks_taxable_income",
    "income_tax",
    "state_income_tax",
    "household_benefits",
    "tax_unit_childcare_expenses",
    "ks_nonrefundable_eitc",
    "ks_refundable_eitc",
    "ks_total_eitc",
]


def run(gift):
    result = pe.us.calculate_household(
        people=[
            {"age": 40, "employment_income": 30_000, "charitable_cash_donations": gift},
            {"age": 8},
        ],
        marital_unit=[{"members": [0]}, {"members": [1]}],
        tax_unit={"filing_status": "HEAD_OF_HOUSEHOLD"},
        spm_unit={"spm_unit_pre_subsidy_childcare_expenses": 3_000},
        household={"state_code": "KS", "county_fips": "20209"},
        year=2026,
        extra_variables=EXTRAS,
    )
    t, h = result.tax_unit, result.household
    return {
        "gift": gift,
        **{name: getattr(t, name) for name in EXTRAS if hasattr(t, name)},
        "household_benefits": h.household_benefits,
        "household_net_income": h.household_net_income,
    }


def main():
    before, after = run(0), run(GIFT)
    report = {
        "hypothetical_household": True,
        "year": 2026,
        "versions": {p: md.version(p) for p in ("policyengine", "policyengine-us")},
        "assumptions": [
            "Kansas full-year resident single parent40, dependent8, qualifying head-of-household",
            "Annual employment wages30000, no other income/deductions",
            "3000 unreimbursed employment-related qualifying childcare expenses",
            "0 versus100 cash gift to eligible public charity, no goods/services or donation-specific credit",
        ],
        "before": before,
        "after": after,
        "net_income_tax_increase": (
            after["income_tax"]
            + after["state_income_tax"]
            - before["income_tax"]
            - before["state_income_tax"]
        ),
        "resource_change_after_gift": after["household_net_income"]
        - before["household_net_income"]
        - GIFT,
        "sources": [
            "https://www.kslegislature.gov/b2025_26/laws/079_000_0000_chapter/079_032_0000_article/079_032_0111c_section/079_032_0111c_k/",
            "https://www.ksrevenue.gov/taxnotices/notice24-09.pdf",
            "https://www.irs.gov/instructions/i2441",
            "https://www.irs.gov/taxtopics/tc506",
        ],
        "limitations": [
            "PolicyEngine estimates use continuous tax schedules; actual filing tax tables and rounding can change exact dollar amounts",
            "Childcare costs qualify under assumed employment, provider, dependent and reimbursement rules",
        ],
    }
    assert before["tax_unit_itemizes"] == after["tax_unit_itemizes"] == 0
    assert before["adjusted_gross_income"] == after["adjusted_gross_income"]
    assert before["household_benefits"] == after["household_benefits"]
    assert report["net_income_tax_increase"] > 0
    assert abs(report["net_income_tax_increase"] - 5) < 0.01
    assert abs(report["resource_change_after_gift"] + 105) < 0.01
    print(json.dumps(report, indent=2))
    Path(__file__).with_suffix(".json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    main()
