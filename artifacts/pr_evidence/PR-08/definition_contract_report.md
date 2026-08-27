# Definition contract

`definition` is required, accepts JSON-compatible values including empty objects/lists, and is validated through canonical serialization. Unsupported values and null definition produce `ResearchBaseError(VALIDATION_ERROR)` before persistence.
