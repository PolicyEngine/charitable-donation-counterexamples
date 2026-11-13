# Charitable donation counterexamples

An ordinary charitable deduction usually saves a fraction of the gift. The broader claim that every gift must cost more than its tax savings has exceptions.

PolicyEngine estimates the following for hypothetical single adults, age 40, under 2026 rules. All amounts compare a full model run with the gift against a full model run without it.

| Scenario | Gift | Tax reduction | Change in money retained after the gift |
| --- | ---: | ---: | ---: |
| Texas, $100,000 wages, ordinary cash donation | $1,000 | $220 | −$780 |
| Arizona, $100,000 wages, qualifying charity credit | $500 | $500 | $0 |
| England, £49,271 wages plus £1,000 savings interest, Gift Aid | £1 | £100.20 | +£99.20 |

## Arizona: a full donation credit

Arizona grants a dollar-for-dollar nonrefundable credit for cash gifts to qualifying charitable organizations. The donor must have enough Arizona income tax liability. The published 2026 single-filer limit is $506, so the $500 gift in this example falls within the limit. PolicyEngine computes state income tax of $2,106.25 without the gift and $1,606.25 with it. Federal income tax stays at $13,170.

This example uses a **tax credit**. The fully credited gift does not also generate a federal charitable deduction: IRS rules reduce the deductible gift by the state credit. The script enters the gift in the Arizona-specific contribution input, leaves federal deductible cash donations at zero, and subtracts the actual $500 outlay from household resources after the model calculation. This prevents double counting.

Sources: [Arizona Department of Revenue](https://azdor.gov/tax-credits/credits-contributions-qcos-and-qfcos), [Arizona Revised Statutes §43-1088](https://www.azleg.gov/ars/43/01088.htm), [IRS Publication 526, state or local tax credit](https://www.irs.gov/publications/p526#en_US_2025_publink1000229175).

## England: Gift Aid restores a larger savings allowance

With £49,271 of wages and £1,000 of taxable savings interest, total income reaches £50,271. The donor has no other income, pension contributions, or reliefs. The Personal Savings Allowance is £500 because the last £1 of income falls above the ordinary £50,270 higher-rate threshold.

A £1 qualifying Gift Aid donation extends the basic-rate band by its £1.25 grossed-up value. The donor then qualifies for the £1,000 Personal Savings Allowance. PolicyEngine computes income tax of £7,440.40 without the gift and £7,340.20 with it. The donor retains £99.20 more after paying the £1 gift. This example reflects a discrete allowance threshold; the gain does not continue for every additional pound donated.

Sources: [HMRC Personal Savings Allowance guidance](https://www.gov.uk/apply-tax-free-interest-on-savings/how-much-is-tax-free), [Income Tax Act 2007 §12B](https://www.legislation.gov.uk/ukpga/2007/3/section/12B), [§414(2)(b), Gift Aid band extension](https://www.legislation.gov.uk/ukpga/2007/3/section/414), [HMRC Gift Aid guidance](https://www.gov.uk/donating-to-charity/gift-aid).

## Scope and reproducibility

These are household examples, not estimates of how many donors experience these outcomes. The Arizona example does not establish a deduction-only US exception. The England example does not establish a US exception. This bounded search does not prove that US deductions can never produce a net gain.

The original claim appears in [this November 12, 2026 post](https://x.com/Sharkyl/status/2120742568900329482). The analysis uses the released `policyengine==6.19.0` wrapper, which pins `policyengine-us==2.2.1` and `policyengine-uk==2.174.1`. The wrapper computes each scenario; arithmetic only compares outputs and subtracts the gift. No reform, population microdata, or behavioral response is used. Model floats are rounded to cents or pence when displayed. UK modeled liabilities abstract from return-entry rounding.

```sh
uv sync --frozen
uv run analyze.py
uv run pytest -q
```

The saved outputs appear in [results.json](results.json). Tests check the examples, the full-credit property for Arizona gifts from $0 to $500 with sufficient liability, and agreement between scalar and vectorized UK calculations. The full-credit property is specific to this scenario; ordinary donations can have a positive net cost.
