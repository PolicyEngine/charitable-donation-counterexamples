"""Check the reported examples and a bounded donation-credit invariant."""

import json
from pathlib import Path

from hypothesis import given, strategies as st
import policyengine as pe
import pytest

from analyze import uk_savings_case


def test_reported_examples():
    results = json.loads(Path("results.json").read_text())
    base, gift = results["texas_ordinary"]
    assert base["federal_income_tax"] - gift["federal_income_tax"] == 220
    assert gift["net_income_after_gift"] - base["net_income_after_gift"] == -780
    base, gift = results["arizona_qco"]
    assert base["state_income_tax"] - gift["state_income_tax"] == 500
    assert gift["net_income_after_gift"] == base["net_income_after_gift"]
    base, gift = results["uk_savings"]
    assert base["savings_allowance"] == 500
    assert gift["savings_allowance"] == 1_000
    assert base["income_tax"] - gift["income_tax"] == pytest.approx(100.20, abs=0.01)


@pytest.fixture(scope="module")
def az_sweep():
    return pe.us.calculate_household(
        people=[{"age": 40, "employment_income": 100_000}],
        tax_unit={"filing_status": "SINGLE"},
        household={"state_code": "AZ", "county_fips": "04013"},
        year=2026,
        axes=[
            [
                {
                    "name": "az_charitable_contributions_to_qualifying_charitable_organizations",
                    "min": 0,
                    "max": 500,
                    "count": 501,
                }
            ]
        ],
        extra_variables=["az_charitable_contributions_credit", "state_income_tax"],
    )


@given(donation=st.integers(min_value=0, max_value=500))
def test_qco_full_credit_for_gifts_below_cap(az_sweep, donation):
    """Enough tax liability: each dollar of gift replaces a dollar of tax."""
    tax = az_sweep.tax_unit.state_income_tax
    credit = az_sweep.tax_unit.az_charitable_contributions_credit
    assert 0 <= credit[donation] <= donation
    assert tax[0] - tax[donation] == pytest.approx(donation, abs=0.01)


def test_uk_individual_and_axis_paths_agree():
    """Differential check of scalar runs against a vectorized sweep."""
    result = pe.uk.calculate_household(
        people=[
            {"age": 40, "employment_income": 49_271, "savings_interest_income": 1_000}
        ],
        household={"region": "LONDON"},
        year=2026,
        axes=[[{"name": "gift_aid", "min": 0, "max": 2, "count": 3}]],
        extra_variables=["income_tax", "savings_allowance"],
    )
    saved = json.loads(Path("results.json").read_text())["uk_savings"]
    for index, row in enumerate(saved):
        assert result.person[0].income_tax[index] == pytest.approx(
            row["income_tax"], abs=0.01
        )
    assert result.person[0].savings_allowance == [500, 1_000, 1_000]
