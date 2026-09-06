# M3 Synthetic Demo Organization Story

The M3 organization is deterministic, hand-authored aggregate demo data. It is not a claim about a real company and was not generated with Faker.

## Shape

- 8 departments: Engineering, Sales, Customer Support, Product, Marketing, Finance, Operations, and Security.
- 19 Department × Role combinations.
- 12 observed months: January–December 2025.
- 6 planning-assumption months: January–June 2026.
- 160 total observed FTE in December 2025; 170.5 aggregate staffing target in January 2026.

## Embedded patterns

- **Increasing Engineering demand:** Software Engineering rises from a January 2026 target of 30 to 32 by June; QA and DevOps also require modest growth. Engineering begins the planning period with a 3-FTE gap.
- **Long Account Executive hiring cycles:** three anonymous completed Sales Account Executive cycles are exactly 90, 105, and 120 days. Their average and median are both 105 days.
- **Elevated recent Support attrition:** Customer Support has five exits in October–December 2025, with a three-month attrition rate of `5 / ((30 + 30 + 28) / 3)`, about 17.0%. It is intentionally the highest recent department attrition rate.
- **Healthy stable Finance:** Finance has 8 observed FTE, an 8-FTE January target, and no recorded hires/exits in the historical period.
- **High-cost, low-gap Security:** Security Engineer costs $21,000 per month but carries only a 0.5-FTE January gap.
- **Lower-cost, substantial Sales need:** Sales Development Representative costs $7,500 per month and begins with a 4-FTE gap; Sales has the largest department gap at 5 FTE overall.
- **Seasonal Support demand:** Support Specialist targets increase from 26 in January to 30 in May and June 2026, reflecting a deliberately simple seasonal service-demand pattern.

The seed is idempotent: it recreates these aggregate demo facts and assumptions on every run, so changes to the story require an intentional code/test/documentation update.
