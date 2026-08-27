# Transaction report

Reconciled by PR-09R: the synchronous UoW owns one database transaction per application command. The original PR-09 evidence did not prove create-run or artifact-attach rollback after a real INSERT and overclaimed atomicity. PR-09R adds injected-after-flush checks for create, dataset attach, artifact attach, start, and finish; fresh UoWs verify exact absence/state/row-version preservation. The existing cross-repository rollback suite remains green.
