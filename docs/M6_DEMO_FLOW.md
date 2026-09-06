# M6 Decision Lab Demo Flow

## Growth + Retention Pressure

This canonical 60--90 second demo uses the existing Sales Development
Representative seed pattern; it does not alter persisted data.

1. Open the Decision Lab and note the persisted baseline forecast.
2. Select **Sales · Sales Development Representative**.
3. Change annual expected attrition from **12%** to **18%**.
4. Change the six monthly targets from **18, 18, 19, 19, 20, 20** to
   **20, 20, 21, 21, 22, 22**.
5. Leave the canonical constrained decision inputs: **$150,000** budget and
   **2 starts/month** capacity.
6. Select **Run Scenario**. The Scenario card shows the no-new-hires effect.
7. Select **Optimize Scenario**. Review the optimized card, trajectory,
   recommendation table, and deterministic explanation.
8. Select **Reset to Baseline** to restore the persisted role assumptions and
   canonical decision inputs.

## Deterministic live result

On the seeded organization, the persisted baseline is `117.610375669416`
understaffed FTE-months. The Growth + Retention Pressure scenario becomes
`131.241909319733`. With the $150,000 / two-starts-per-month constraints, the
authoritative optimizer reduces that to `111.567259688633`, using all $150,000
for eight Sales Development Representative starts arriving in Months 3--6.

The scenario therefore makes the forecast worse by `13.631533650317`
FTE-months; optimization recovers `19.674649631100` FTE-months relative to the
scenario. The allocation is a model consequence, not a priority judgment.

The result is intentionally transparent: concentrated Sales allocation is a
consequence of staffing shortages, role cost, lead time, the six-month horizon,
and the objective of minimizing total understaffed FTE-months. It is not a
claim that Sales is more strategically important than other functions.
