"""
Neo4j Aura Free client.
Stores the code knowledge graph: Function and Class nodes
connected by CALLS relationships.
"""

import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()


class GraphDB:
    def __init__(self) -> None:
        uri = os.getenv("NEO4J_URI")
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD")

        if not uri or not password:
            raise ValueError(
                "NEO4J_URI and NEO4J_PASSWORD must be set in .env. "
                "Get them from console.neo4j.io (AuraDB Free)."
            )

        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def verify(self) -> bool:
        """Check the connection is alive."""
        self.driver.verify_connectivity()
        return True

    def close(self) -> None:
        self.driver.close()

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    def clear(self) -> None:
        """Delete all nodes and relationships. Call before loading a new repo."""
        with self.driver.session() as s:
            s.run("MATCH (n) DETACH DELETE n")

    def load_nodes(self, nodes: list[dict]) -> None:
        function_nodes = [n for n in nodes if n["type"] == "function"]
        class_nodes = [n for n in nodes if n["type"] == "class"]

        call_edges = []
        for n in function_nodes:
            for callee in n.get("calls", []):
                call_edges.append({"caller": n["name"], "callee": callee})

        with self.driver.session() as s:
            if function_nodes:
                s.run(
                    """
                    UNWIND $rows AS row
                    MERGE (f:Function {name: row.name, file: row.file})
                    SET f.cls = row.cls, f.start_line = row.line
                    """,
                    rows=[
                        {
                            "name": n["name"],
                            "file": n["file"],
                            "cls": n.get("class", ""),
                            "line": n.get("start_line", 0),
                        }
                        for n in function_nodes
                    ],
                )

            if class_nodes:
                s.run(
                    """
                    UNWIND $rows AS row
                    MERGE (c:Class {name: row.name, file: row.file})
                    """,
                    rows=[{"name": n["name"], "file": n["file"]} for n in class_nodes],
                )

            if call_edges:
                s.run(
                    """
                    UNWIND $rows AS row
                    MERGE (a:Function {name: row.caller})
                    MERGE (b:Function {name: row.callee})
                    MERGE (a)-[:CALLS]->(b)
                    """,
                    rows=call_edges,
                )

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    def get_neighbors(self, fn_name: str, depth: int = 2) -> list[dict]:
        """
        Return functions reachable from fn_name within `depth` hops
        via CALLS relationships (in either direction).
        """
        with self.driver.session() as s:
            result = s.run(
                """
                MATCH (start:Function {name: $name})-[*1..$depth]-(neighbor:Function)
                RETURN DISTINCT neighbor.name AS name, neighbor.file AS file
                LIMIT 15
                """,
                name=fn_name,
                depth=depth,
            )
            return [dict(r) for r in result]

    def query(self, cypher: str, **params) -> list[dict]:
        """Run arbitrary read Cypher and return rows as dicts."""
        with self.driver.session() as s:
            return [dict(r) for r in s.run(cypher, **params)]

    def stats(self) -> dict:
        """Return counts of functions, classes, and edges."""
        with self.driver.session() as s:
            counts = s.run(
                """
                MATCH (n) RETURN
                  count(CASE WHEN n:Function THEN 1 END) AS fns,
                  count(CASE WHEN n:Class    THEN 1 END) AS classes
                """
            ).single()

            edges = s.run(
                "MATCH ()-[r:CALLS]->() RETURN count(r) AS e"
            ).single()

            return {
                "functions": counts["fns"],
                "classes": counts["classes"],
                "edges": edges["e"],
            }
