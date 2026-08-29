# Duplicate edge error translation report

`SqlAlchemyStatisticalResultRepository.add_input()` catches an
`IntegrityError` only when its original message names
`statistical_result_inputs_pkey`. It rolls back the failed transaction and
raises the existing stable `ResearchBaseError` with code `VALIDATION_ERROR`,
using `raise ... from exc` so the database exception remains available as
`__cause__`. Other integrity errors are re-raised unchanged.

The direct repository/UoW duplicate-edge regression observed the stable public
error, an `IntegrityError` cause, no raw error escape, and no persisted parent
or edge in a fresh UoW.
