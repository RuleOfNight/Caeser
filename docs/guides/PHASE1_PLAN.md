# Code Intelligence System --- Phase 1

## Objective

Build a minimal system to parse code, build a graph, and explain
relationships.

## Architecture

repo → ingestion → parsing → extraction → graph → query → explain

## Modules

-   ingestion: scan files
-   parsing: AST
-   extraction: functions, calls
-   graph: networkx graph
-   query: graph traversal
-   explain: text output

## Constraints

-   Python only
-   No LLM
-   No over-engineering

## Done Criteria

-   Parse repo
-   Build graph
-   Query function
-   Output explanation
