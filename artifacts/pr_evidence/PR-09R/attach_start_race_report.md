# Attach-vs-start race report

The test uses two independent SQLAlchemy UoWs/connections and a `threading.Barrier` installed at `SqlAlchemyRunRepository.get_for_update`. A protected counter proves both workers reached the synchronization point before either lock decision completes.

The observed serializations are safe under row-version semantics:

1. Start wins: start commits sealing; attach receives stable `IMMUTABLE_RECORD` and no edge is added.
2. Attach wins: the original stale start receives `CONCURRENT_MODIFICATION`; a fresh row-version start then seals the committed edge.

Both final states are checked with a fresh UoW. No input edge is committed after `inputs_sealed_at`.
