# Charitable donation counterexamples

An ordinary charitable deduction usually saves a fraction of the gift. The broader claim that every gift must cost more than its tax savings has exceptions.

PolicyEngine estimates the following for hypothetical adults, age 40, under 2026 rules. All amounts compare a full model run with the gift against a full model run without it.

| Scenario | Gift | Tax reduction | Change in money retained after the gift |
| --- | ---: | ---: | ---: |
| Texas, $100,000 wages, ordinary cash donation | $1,000 | $220 | −$780 |
| Arizona, $100,000 wages, qualifying charity credit | $500 | $500 | $0 |
| Iowa, single parent with $114,150 wages and $3,000 qualifying childcare costs | $10 | $182.58 | +$172.58 |
| England, £49,271 wages plus £1,000 savings interest, Gift Aid | £1 | £100.20 | +£99.20 |

## Iowa: a deduction restores a refundable childcare credit

A hypothetical Iowa head-of-household filer, age 40, supports an eight-year-old and pays $3,000 in unreimbursed, employment-related qualifying childcare expenses. The parent earns $114,150 and has no other income or deductions. Before giving, the $24,150 standard deduction leaves federal and Iowa taxable income at $90,000.

A $10 cash gift to an eligible charity qualifies for the 2026 federal deduction for nonitemizers and reduces taxable income to $89,990. Iowa's refundable childcare credit increases from zero to $180 because eligibility requires taxable income below $90,000. Federal income tax falls by $2.20 and Iowa net income tax falls by $180.38. Total tax savings of about $182.58 exceed the gift by $172.58. Both runs use the standard deduction; neither uses a donation tax credit. The new charitable deduction reduces taxable income, while adjusted gross income stays unchanged.

Sources: [Iowa Code §422.7, federal taxable income starting point](https://www.legis.iowa.gov/docs/code/2026/422.7.pdf), [§422.12C, refundable childcare credit](https://www.legis.iowa.gov/docs/code/2026/422.12C.pdf), [Iowa refundable childcare credit instructions](https://revenue.iowa.gov/taxes/tax-guidance/individual-income-tax/1040-expanded-instructions/child-dependent-care-credit), [IRS charitable contributions guidance](https://www.irs.gov/taxtopics/tc506). Run `uv run iowa_counterexample.py` to reproduce the complete before/after calculations in [iowa_counterexample.json](iowa_counterexample.json). Federal Tax Table return rounding can change the precise filed liability. Model floating-point arithmetic also causes a difference of less than one cent between the direct tax comparison and the net-income comparison; displayed figures use the tax comparison.

## Arizona: a full donation credit

Arizona grants a dollar-for-dollar nonrefundable credit for cash gifts to qualifying charitable organizations. The donor must have enough Arizona income tax liability. The published 2026 single-filer limit is $506, so the $500 gift in this example falls within the limit. PolicyEngine computes state income tax of $2,106.25 without the gift and $1,606.25 with it. Federal income tax stays at $13,170.

This example uses a **tax credit**. The fully credited gift does not also generate a federal charitable deduction: IRS rules reduce the deductible gift by the state credit. The script enters the gift in the Arizona-specific contribution input, leaves federal deductible cash donations at zero, and subtracts the actual $500 outlay from household resources after the model calculation. This prevents double counting.

Sources: [Arizona Department of Revenue](https://azdor.gov/tax-credits/credits-contributions-qcos-and-qfcos), [Arizona Revised Statutes §43-1088](https://www.azleg.gov/ars/43/01088.htm), [IRS Publication 526, state or local tax credit](https://www.irs.gov/publications/p526#en_US_2025_publink1000229175).

## England: Gift Aid restores a larger savings allowance

With £49,271 of wages and £1,000 of taxable savings interest, total income reaches £50,271. The donor has no other income, pension contributions, or reliefs. The Personal Savings Allowance is £500 because the last £1 of income falls above the ordinary £50,270 higher-rate threshold.

A £1 qualifying Gift Aid donation extends the basic-rate band by its £1.25 grossed-up value. The donor then qualifies for the £1,000 Personal Savings Allowance. PolicyEngine computes income tax of £7,440.40 without the gift and £7,340.20 with it. The donor retains £99.20 more after paying the £1 gift. This example reflects a discrete allowance threshold; the gain does not continue for every additional pound donated.

Sources: [HMRC Personal Savings Allowance guidance](https://www.gov.uk/apply-tax-free-interest-on-savings/how-much-is-tax-free), [Income Tax Act 2007 §12B](https://www.legislation.gov.uk/ukpga/2007/3/section/12B), [§414(2)(b), Gift Aid band extension](https://www.legislation.gov.uk/ukpga/2007/3/section/414), [HMRC Gift Aid guidance](https://www.gov.uk/donating-to-charity/gift-aid).

## Scope and reproducibility

These are household examples, not estimates of how many donors experience these outcomes. The Arizona example uses a credit and the England example uses UK tax rules. The Iowa example establishes a US deduction interaction under the model's 2026 rules. These examples do not describe the return to each additional dollar of giving away from the thresholds.

The original claim appears in [this November 12, 2026 post](https://x.com/Sharkyl/status/2120742568900329482). The analysis uses the released `policyengine==6.19.0` wrapper, which pins `policyengine-us==2.2.1` and `policyengine-uk==2.174.1`. The wrapper computes each scenario; arithmetic only compares outputs and subtracts the gift. The synthetic examples use no reform, population microdata, or behavioral response. Model floats are rounded to cents or pence when displayed. UK modeled liabilities abstract from return-entry rounding.

The population search runs the certified `populace_us_2024` Microcosm dataset under 2026 policy. It adds ordinary cash gifts to existing donations for each model tax-unit head, preserves all special state-credit inputs, and recomputes taxes, benefits, and net income. Each amount runs in a separate process after a common baseline; the $0 control must reproduce the baseline. `population_search.py` uses MicroSeries for weighted operations and `map_to` for entity transfers. Record-level output stays in ignored `private_outputs/`; summaries contain aggregates only. Apparent gains require a separate check of legal filing choices and numerical precision before any prevalence interpretation.

On Max's machine, run the population work through the shared heavy-job guard:

```sh
~/reviews/us-hub/scripts/heavy_run.sh donation-search uv run run_population_search.py
uv run inspect_population.py
```

```sh
uv sync --frozen
uv run analyze.py
uv run pytest -q
```

The saved outputs appear in [results.json](results.json). Tests check the examples, the full-credit property for Arizona gifts from $0 to $500 with sufficient liability, and agreement between scalar and vectorized UK calculations. The full-credit property is specific to this scenario; ordinary donations can have a positive net cost.
