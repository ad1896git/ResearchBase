# Transaction report

Create, add-version, draft edit, freeze, and current-pointer operations use synchronous
SQLAlchemy UnitOfWork transactions. ArtifactVersion registration does not begin its DB
transaction until store verification has succeeded. Parent locking, version insertion,
pointer movement, and superseding the prior frozen version occur in the same transaction.

The rollback test confirms that an injected commit failure leaves zero database rows while
preserving the already verified store object; a retry then registers exactly one row.
