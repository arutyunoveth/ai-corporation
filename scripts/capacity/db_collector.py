from __future__ import annotations

import os
import sys

_DB_QUERIES = {
    "database_size": "SELECT pg_database_size(current_database()) AS bytes",
    "extension_vector": (
        "SELECT version FROM pg_extension WHERE extname = 'vector'"
    ),
    "vector_columns": """
        SELECT
            n.nspname AS schema_name,
            c.relname AS table_name,
            a.attname AS column_name,
            format_type(a.atttypid, a.atttypmod) AS declared_type
        FROM pg_attribute a
        JOIN pg_class c ON a.attrelid = c.oid
        JOIN pg_namespace n ON c.relnamespace = n.oid
        JOIN pg_type t ON a.atttypid = t.oid
        WHERE t.typname IN ('vector', 'halfvec', 'sparsevec')
          AND a.attnum > 0
          AND NOT a.attisdropped
          AND n.nspname NOT IN ('pg_catalog', 'information_schema')
        ORDER BY n.nspname, c.relname, a.attnum
    """,
    "relation_sizes": """
        SELECT
            n.nspname AS schema_name,
            c.relname AS table_name,
            c.reltuples::BIGINT AS approximate_row_count,
            pg_table_size(c.oid) AS heap_bytes,
            pg_indexes_size(c.oid) AS indexes_bytes,
            pg_total_relation_size(c.oid) AS total_bytes
        FROM pg_class c
        JOIN pg_namespace n ON c.relnamespace = n.oid
        WHERE c.relkind = 'r'
          AND n.nspname NOT IN ('pg_catalog', 'information_schema')
        ORDER BY pg_total_relation_size(c.oid) DESC
    """,
    "dead_tuple_stats": """
        SELECT
            schemaname AS schema_name,
            relname AS table_name,
            n_live_tup,
            n_dead_tup,
            last_analyze,
            last_autoanalyze
        FROM pg_stat_user_tables
        WHERE n_dead_tup > 0
        ORDER BY n_dead_tup DESC
    """,
    "index_sizes": """
        SELECT
            n.nspname AS schema_name,
            c.relname AS table_name,
            i.relname AS index_name,
            pg_relation_size(i.oid) AS index_bytes
        FROM pg_class i
        JOIN pg_index idx ON i.oid = idx.indexrelid
        JOIN pg_class c ON idx.indrelid = c.oid
        JOIN pg_namespace n ON c.relnamespace = n.oid
        WHERE i.relkind = 'i'
          AND n.nspname NOT IN ('pg_catalog', 'information_schema')
        ORDER BY pg_relation_size(i.oid) DESC
    """,
    "schema_totals": """
        SELECT
            n.nspname AS schema_name,
            SUM(pg_total_relation_size(c.oid)) AS total_bytes
        FROM pg_class c
        JOIN pg_namespace n ON c.relnamespace = n.oid
        WHERE c.relkind = 'r'
          AND n.nspname NOT IN ('pg_catalog', 'information_schema')
        GROUP BY n.nspname
        ORDER BY total_bytes DESC
    """,
}


def collect_database_metrics(dsn: str, timeout_s: int = 30) -> dict:
    metrics: dict = {
        "available": False,
        "error": None,
        "database_size_bytes": None,
        "pgvector_version": None,
        "vector_columns": [],
        "relations": [],
        "dead_tuple_stats": [],
        "index_sizes": [],
        "schema_totals": [],
        "row_count_kind": None,
        "warnings": [],
    }
    try:
        import psycopg
    except ImportError:
        metrics["error"] = "psycopg not available"
        metrics["warnings"].append("psycopg not installed; cannot connect to PostgreSQL")
        return metrics
    conn = None
    try:
        conn = psycopg.connect(dsn, connect_timeout=10)
        with conn.cursor() as cur:
            cur.execute("SET default_transaction_read_only = on")
            cur.execute(f"SET statement_timeout = '{timeout_s}s'")

            cur.execute(_DB_QUERIES["database_size"])
            row = cur.fetchone()
            if row:
                metrics["database_size_bytes"] = int(row[0])

            cur.execute(_DB_QUERIES["extension_vector"])
            row = cur.fetchone()
            if row:
                metrics["pgvector_version"] = str(row[0])

            cur.execute(_DB_QUERIES["vector_columns"])
            vector_cols = []
            for row in cur.fetchall():
                vector_cols.append({
                    "schema_name": row[0],
                    "table_name": row[1],
                    "column_name": row[2],
                    "declared_type": row[3],
                })
            metrics["vector_columns"] = vector_cols

            cur.execute(_DB_QUERIES["relation_sizes"])
            relations = []
            for row in cur.fetchall():
                relations.append({
                    "schema_name": row[0],
                    "table_name": row[1],
                    "approximate_row_count": int(row[2]) if row[2] is not None else None,
                    "heap_bytes": int(row[3]) if row[3] is not None else 0,
                    "indexes_bytes": int(row[4]) if row[4] is not None else 0,
                    "total_bytes": int(row[5]) if row[5] is not None else 0,
                })
            metrics["relations"] = relations
            metrics["row_count_kind"] = "estimated"

            try:
                cur.execute(_DB_QUERIES["dead_tuple_stats"])
                dead_stats = []
                for row in cur.fetchall():
                    dead_stats.append({
                        "schema_name": row[0],
                        "table_name": row[1],
                        "n_live_tup": int(row[2]) if row[2] is not None else 0,
                        "n_dead_tup": int(row[3]) if row[3] is not None else 0,
                        "last_analyze": str(row[4]) if row[4] is not None else None,
                        "last_autoanalyze": str(row[5]) if row[5] is not None else None,
                    })
                metrics["dead_tuple_stats"] = dead_stats
            except Exception as exc:
                metrics["warnings"].append(f"dead_tuple_stats unavailable: {exc}")

            try:
                cur.execute(_DB_QUERIES["index_sizes"])
                index_sizes = []
                for row in cur.fetchall():
                    index_sizes.append({
                        "schema_name": row[0],
                        "table_name": row[1],
                        "index_name": row[2],
                        "index_bytes": int(row[3]) if row[3] is not None else 0,
                    })
                metrics["index_sizes"] = index_sizes
            except Exception as exc:
                metrics["warnings"].append(f"index_sizes unavailable: {exc}")

            try:
                cur.execute(_DB_QUERIES["schema_totals"])
                schema_totals = []
                for row in cur.fetchall():
                    schema_totals.append({
                        "schema_name": row[0],
                        "total_bytes": int(row[1]) if row[1] is not None else 0,
                    })
                metrics["schema_totals"] = schema_totals
            except Exception as exc:
                metrics["warnings"].append(f"schema_totals unavailable: {exc}")

        metrics["available"] = True
    except Exception as exc:
        metrics["error"] = str(exc)
        metrics["warnings"].append(f"database connection or query failed: {exc}")
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
    return metrics
