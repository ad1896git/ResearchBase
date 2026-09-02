# SQL / Output Report

For each representative CLI query, direct Application SQL and CLI SQL counts were equal. All observed CLI
statements were SELECT statements. Dataclass serialization occurs after the query service returns and adds zero
database reads. No lazy ORM object crosses the Application boundary.
