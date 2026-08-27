# Transaction report

Application create, freeze, and revise each use one UoW transaction. Failure after flush was injected for each path. PostgreSQL verification showed create left no identity/version rows, freeze left the exact DRAFT/pointer pre-state, and revise left no child version, supersede mutation, or pointer change. No repository performs commit.
