# Atomicity report

Finding, assessment+targets, and correction creation were each fault-injected after real repository SQL/flush. Every failure rolled back through UoW exit; a fresh connection observed zero partial rows; retry produced exact cardinality one.
