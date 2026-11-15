# Results

Generated from the verified Kaggle CSV. See methodology and limitations before interpreting.

| segment       |     n |   conversions |   conversion_rate |   visit_rate |   revenue_per_customer |
|:--------------|------:|--------------:|------------------:|-------------:|-----------------------:|
| No E-Mail     | 21306 |           122 |        0.00572609 |     0.106167 |               0.652789 |
| Mens E-Mail   | 21307 |           267 |        0.0125311  |     0.182757 |               1.42262  |
| Womens E-Mail | 21387 |           189 |        0.00883714 |     0.1514   |               1.0772   |

## Primary comparisons

| arm           |     effect |   relative_lift |     p_value |     ci_low |    ci_high |   family_ci_low |   family_ci_high |      p_holm |
|:--------------|-----------:|----------------:|------------:|-----------:|-----------:|----------------:|-----------------:|------------:|
| Mens E-Mail   | 0.00680501 |        1.18842  | 1.52322e-13 | 0.00501434 | 0.00864072 |      0.00475791 |       0.00891088 | 3.04645e-13 |
| Womens E-Mail | 0.00311106 |        0.543313 | 0.000157105 | 0.00150166 | 0.00474547 |      0.00126922 |       0.00498551 | 0.000157105 |

## Exploratory revenue

| arm           |   effect |     p_value |   ci_low |   ci_high |   bootstrap_low |   bootstrap_high |
|:--------------|---------:|------------:|---------:|----------:|----------------:|-----------------:|
| Mens E-Mail   | 0.769827 | 1.16381e-07 | 0.48514  |  1.05451  |        0.476611 |          1.05171 |
| Womens E-Mail | 0.424412 | 0.0011294   | 0.168957 |  0.679868 |        0.162705 |          0.67848 |

SRM p=0.903693; maximum absolute baseline SMD=0.0137.

Planning MDE at 80% power: 0.247 percentage points.