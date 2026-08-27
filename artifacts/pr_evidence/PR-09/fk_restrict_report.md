# FK RESTRICT report

PostgreSQL constraint inspection confirmed seven PR-09 foreign keys with `ON DELETE RESTRICT`. A behavioral test attempted to delete a Run with attached inputs and PostgreSQL rejected the delete; the Run remained present. The exact dataset/artifact/spec/project/actor references are concrete FKs.

