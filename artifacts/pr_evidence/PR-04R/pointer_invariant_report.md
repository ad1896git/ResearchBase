# PR-04R Pointer Invariant Report

Database foreign keys prove that a current pointer target exists. They do not prove that it belongs to the same parent. The Application/repository ownership check supplies that invariant.

- ResearchQuestion A was given ResearchQuestion B's version ID through `freeze_research_question`; the command returned `REFERENTIAL_INTEGRITY_ERROR`, and A's persisted pointer remained unchanged.
- Hypothesis A was given Hypothesis B's version ID through `freeze_hypothesis`; the command returned `REFERENTIAL_INTEGRITY_ERROR`, and A's persisted pointer remained unchanged.

No unnecessary composite foreign key was added.
