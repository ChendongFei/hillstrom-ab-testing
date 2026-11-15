# Analysis specification and statistical reasoning

## Context and estimand
The original source describes customers who purchased in the preceding year, randomized approximately equally to Mens email, Womens email or no email, with two-week outcomes. Email names describe creative content, not customer gender. The experimental unit is the customer as represented by one supplied row; a real unique customer ID is not available to verify this.

Primary outcome: any purchase within two weeks (`conversion`). Denominator: all assigned customers. Estimate two intent-to-treat risk differences, each email minus no email. Do not restrict to visitors, purchasers or delivered-email recipients: these are post-assignment selections. Potential-outcome interpretation requires consistency, no interference, independent units, faithful random assignment and complete, nondifferential measurement. The extract supports a conditional causal reanalysis rather than independent verification of these assumptions.

H0 for each comparison: purchase probabilities are equal; H1: they differ. Two-sided alpha=0.05 for the family of two primary tests. This specification was documented retrospectively with outcomes already accessible and is not a preregistration.

## Tests and uncertainty
- Pooled two-proportion z tests: randomized independent binary outcomes, sufficiently large successes/failures in each arm. The pooled variance corresponds to the null of equal probabilities. Tests explicitly handle all-zero/all-one totals. A unit test independently checks equivalence to Pearson's 2x2 chi-square test without continuity correction.
- Holm correction: controls family-wise error across the two primary comparisons, including their dependence through a shared control. No claim is based on cherry-picking unadjusted significance.
- Newcombe differences of Wilson intervals: marginal 95% uncertainty for absolute effects, avoiding the simplest Wald interval. Also report 97.5% intervals for two-comparison Bonferroni simultaneous coverage (approximate because component intervals are approximate). These are not exact inversions of Holm tests; report methods distinctly.
- Relative lift = (treatment/control)-1. It can appear large when baseline risk is low. Absolute percentage points and incremental purchases per 10,000 clarify scale. Confidence intervals focus on absolute effects.
- Revenue per assigned customer includes zeros. Welch's t test and its 95% interval allow unequal variances and target a mean difference, with large-sample justification rather than assuming individual spend is normal. Seeded ordinary within-arm nonparametric bootstrap (3,000 replicates, percentile interval) checks sensitivity to heavy skew. Multinomial resampling over unique values is mathematically equivalent to resampling rows for this statistic. Bootstrap does not resolve missing customers, confounding or dependence. Revenue analyses are exploratory, unadjusted and not a second confirmatory family. Visit rates are descriptive.
- Do not use a normality-test gatekeeper to switch automatically to Mann–Whitney: that would change the estimand away from mean revenue. Do not remove valid high spend simply because it is extreme.

## Quality and experiment checks
Validate exact schema, missingness, binary support, finite nonnegative monetary values, recency 1–12, all expected arms, and outcome coherence (purchase implies visit and positive spend matches conversion). Fail loudly on violations. Preserve exact-profile repeats because true duplicate customer identities cannot be established. Source SHA-256 fixes the analysis input. Cleaning is limited to a documented location-label typo.

SRM uses a Pearson goodness-of-fit chi-square statistic with two degrees of freedom and expected probabilities 1/3 each, following the original description. Exact assignment implementation is unavailable; if fixed quotas or stratification were used, this multinomial diagnostic is only approximate. Use 0.001 as an investigation flag, not proof of validity at larger p. No exclusions are made based on SRM.

Baseline balance uses standardized mean differences for history, recency, purchase flags, new-customer flag, and one-hot channel/location. It is descriptive; a reference magnitude of 0.1 is an investigation aid, not a formal validation criterion. `history_segment` is redundant with continuous history. Never adjust for post-treatment spend/visit when estimating the conversion effect.

## Power and decision relevance
Power tables are future-design sensitivity analyses, not observed post-hoc power. Use the observed control rate as an explicitly uncertain planning baseline, equal group sizes, 80% power and conservative per-comparison alpha=0.025. The normal approximation with Cohen's arcsine h gives a positive-direction MDE of about 0.247 percentage points at 21,306 per arm. This does not prove the original experiment was adequately planned. For example, detecting a 0.10 pp increase needs approximately 117,433 per arm under these assumptions. Future studies should vary baseline assumptions, specify a commercially meaningful effect and allow for tracking losses.

No minimum business-worthy effect is invented for the historical campaign. Statistical significance alone cannot establish value. Costs, margins and long-run harms are needed before rollout. No equivalence claim follows from a nonsignificant comparison.

## Unresolved issues
No IDs or assignment/ingestion logs to verify independence, duplicate identity, attrition or exclusions; no household clusters; no timestamps to check concurrent operation or peeking; no original stopping rule or predeclared primary outcome; source-era retail sample limits transportability; no deliverability or spillover measurement; sparse purchases constrain subgroup precision; no experimental costs/profit margins or customer-harm guardrails. External replication, multiplicity-aware new experiments and verified business inputs remain necessary. Targeting/uplift models are deliberately out of scope until this baseline is understood and an honest holdout evaluation is designed.
