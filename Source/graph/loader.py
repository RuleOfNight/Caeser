import json
import os
from pathlib import Path

from neo4j import GraphDatabase

_EDGE_MERGE = {
    "IMPORTS":  "MERGE (a)-[r:IMPORTS]->(b)  SET r.confidence=$confidence",
    "DEFINES":  "MERGE (a)-[r:DEFINES]->(b)  SET r.confidence=$confidence",
    "CONTAINS": "MERGE (a)-[r:CONTAINS]->(b) SET r.confidence=$confidence",
    "CALLS":    "MERGE (a)-[r:CALLS]->(b)    SET r.confidence=$confidence",
    "INHERITS": "MERGE (a)-[r:INHERITS]->(b) SET r.confidence=$confidence",
}

_NODE_MERGE = (
    "MERGE (n:{label} {{id: $id}}) "
    "SET n.name=$name, n.file_path=$file_path, n.line_start=$line_start, "
    "n.docstring=$docstring, n.is_async=$is_async, n.decorators=$decorators"
)

_CONSTRAINTS = [
    "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Module)   REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Class)    REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Function) REQUIRE n.id IS UNIQUE",
]


def load(
    json_path: str,
    uri: str = None,
    user: str = None,
    password: str = None,
) -> None:
    uri      = uri      or os.environ.get("NEO4J_URI")
    user     = user     or os.environ.get("NEO4J_USER")
    password = password or os.environ.get("NEO4J_PASSWORD")

    data = json.loads(Path(json_path).read_text(encoding="utf-8"))
    nodes = data["nodes"]
    edges = [e for e in data["edges"] if e["confidence"] > 0.0]

    driver = GraphDatabase.driver(uri, auth=(user, password))
    try:
        with driver.session() as session:
            for cql in _CONSTRAINTS:
                session.run(cql)

            for node in nodes:
                label = node["type"]  # "Module" | "Class" | "Function"
                session.run(
                    _NODE_MERGE.format(label=label),
                    id=node["id"],
                    name=node["name"],
                    file_path=node["file_path"],
                    line_start=node["line_start"],
                    docstring=node.get("docstring"),
                    is_async=node.get("is_async", False),
                    decorators=node.get("decorators", []),
                )

            loaded_edges = 0
            for edge in edges:
                merge_cql = _EDGE_MERGE.get(edge["type"])
                if not merge_cql:
                    continue
                session.run(
                    f"MATCH (a {{id: $source_id}}), (b {{id: $target_id}}) {merge_cql}",
                    source_id=edge["source_id"],
                    target_id=edge["target_id"],
                    confidence=edge["confidence"],
                )
                loaded_edges += 1
    finally:
        driver.close()

    print(f"[+] Neo4j loaded: {len(nodes)} nodes | {loaded_edges} edges")
    print(f"    Project: {data.get('project')} | URI: {uri}")
