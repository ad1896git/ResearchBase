# Unit compatibility report

The compatibility rule is exact equality only when both units are non-null. A metric
unit mismatch is rejected with VALIDATION_ERROR; no conversion or normalization is
performed. A null measurement unit is allowed when the metric has a unit, and either
unit may be supplied when the metric unit is null. Unit length is bounded at 64
characters by the domain contract.

Result: PASS.
