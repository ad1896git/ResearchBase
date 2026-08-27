# History query report

History is parent-filtered and ordered by `version_number`, retains superseded and draft statuses, and is returned as application read models rather than ORM objects. The PR-08 application test verifies a two-version history and current pointer.
