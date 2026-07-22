from __future__ import annotations

import math
import re

_VECTOR_KINDS = {"vector": 4, "halfvec": 2, "sparsevec": None}
_VECTOR_ACCESS_METHODS = frozenset({"hnsw", "ivfflat"})
_VECTOR_TYPENAMES = frozenset(_VECTOR_KINDS)

_STATEMENT_TIMEOUT_MIN = 1
_STATEMENT_TIMEOUT_MAX = 300

_DB_QUERIES = {
    "database_size": "SELECT pg_database_size(current_database()) AS bytes",
    "read_only": "SHOW default_transaction_read_only",
    "txn_read_only": "SHOW transaction_read_only",
    "extension_vector": (
        "SELECT extversion FROM pg_extension WHERE extname = 'vector'"
    ),
    "vector_columns": """
        SELECT
            n.nspname AS schema_name,
            c.relname AS table_name,
            a.attname AS column_name,
            format_type(a.atttypid, a.atttypmod) AS declared_type,
            t.typname AS vector_kind
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
            pg_relation_size(c.oid) AS main_fork_bytes,
            pg_table_size(c.oid) AS table_bytes,
            COALESCE(
                (SELECT pg_relation_size(c.reltoastrelid)
                 FROM pg_class tc
                 WHERE tc.oid = c.reltoastrelid),
                0
            ) AS toast_total_bytes,
            pg_indexes_size(c.oid) AS indexes_bytes,
            pg_total_relation_size(c.oid) AS total_bytes
        FROM pg_class c
        JOIN pg_namespace n ON c.relnamespace = n.oid
        WHERE c.relkind = 'r'
          AND n.nspname NOT IN ('pg_catalog', 'information_schema')
        ORDER BY pg_total_relation_size(c.oid) DESC
    """,
    "index_details": """
        SELECT
            n.nspname AS schema_name,
            c.relname AS table_name,
            i.relname AS index_name,
            pg_relation_size(i.oid) AS index_bytes,
            a.amname AS access_method
        FROM pg_index idx
        JOIN pg_class i ON idx.indexrelid = i.oid
        JOIN pg_class c ON idx.indrelid = c.oid
        JOIN pg_namespace n ON c.relnamespace = n.oid
        JOIN pg_am a ON i.relam = a.oid
        WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
        ORDER BY pg_relation_size(i.oid) DESC
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


def _parse_vector_dimension(declared_type: str) -> int | None:
    m = re.search(r"\((\d+)\)", declared_type)
    if m:
        return int(m.group(1))
    return None


def _safe_error_code(exc: Exception) -> dict:
    type_name = type(exc).__name__
    return {"code": "database_query_failed", "error_type": type_name}


def _check_read_only(conn, timeout_s: int) -> bool:
    with conn.cursor() as cur:
        cur.execute(f"SET statement_timeout = '{timeout_s}s'")
        cur.execute("SET default_transaction_read_only = on")
        cur.execute("SHOW default_transaction_read_only")
        row = cur.fetchone()
        if not row or row[0] != "on":
            return False
        cur.execute("SHOW transaction_read_only")
        row = cur.fetchone()
        if row and row[0] == "on":
            return True
        cur.execute("BEGIN")
        cur.execute("SHOW transaction_read_only")
        row = cur.fetchone()
        cur.execute("ROLLBACK")
        return bool(row and row[0] == "on")


def _run_metric(cur, name: str, query: str) -> dict:
    try:
        cur.execute(query)
        rows = cur.fetchall()
        return {"status": "ok", "rows": rows, "error": None}
    except Exception as exc:
        try:
            cur.execute("ROLLBACK")
        except Exception:
            pass
        return {"status": "unavailable", "rows": [], "error": _safe_error_code(exc)}


def collect_database_metrics(dsn: str, timeout_s: int = 30) -> dict:
    timeout_s = max(_STATEMENT_TIMEOUT_MIN, min(timeout_s, _STATEMENT_TIMEOUT_MAX))
    metrics: dict = {
        "available": False,
        "read_only_verified": False,
        "error": None,
        "database_size_bytes": None,
        "pgvector_version": None,
        "vector_columns": [],
        "relations": [],
        "index_details": [],
        "dead_tuple_stats": [],
        "schema_totals": [],
        "row_count_kind": None,
        "metric_status": {},
        "warnings": [],
    }
    try:
        import psycopg
    except ImportError:
        metrics["error"] = {"code": "psycopg_not_available", "error_type": "ImportError"}
        metrics["warnings"].append("psycopg not installed")
        return metrics

    conn = None
    try:
        conn = psycopg.connect(dsn, connect_timeout=10)
        conn.read_only = True
        read_only_ok = _check_read_only(conn, timeout_s)
        metrics["read_only_verified"] = read_only_ok
        if not read_only_ok:
            metrics["error"] = {"code": "read_only_verification_failed", "error_type": "RuntimeError"}
            metrics["warnings"].append("read-only verification failed")
            return metrics

        metrics["available"] = True

        with conn.cursor() as cur:
            ms = _run_metric(cur, "database_size", _DB_QUERIES["database_size"])
            metrics["metric_status"]["database_size"] = ms["status"]
            if ms["status"] == "ok" and ms["rows"]:
                metrics["database_size_bytes"] = int(ms["rows"][0][0])

            ms = _run_metric(cur, "pgvector_extension", _DB_QUERIES["extension_vector"])
            metrics["metric_status"]["pgvector_extension"] = ms["status"]
            if ms["status"] == "ok" and ms["rows"]:
                metrics["pgvector_version"] = str(ms["rows"][0][0])

            ms = _run_metric(cur, "vector_columns", _DB_QUERIES["vector_columns"])
            metrics["metric_status"]["vector_columns"] = ms["status"]
            if ms["status"] == "ok":
                raw_cols = ms["rows"]
            else:
                raw_cols = []
            vector_cols = []
            for row in raw_cols:
                declared_type = row[3]
                vkind = row[4]
                dim = _parse_vector_dimension(declared_type)
                vc = {
                    "schema_name": row[0],
                    "table_name": row[1],
                    "column_name": row[2],
                    "declared_type": declared_type,
                    "vector_kind": vkind,
                    "declared_dimension": dim,
                    "approximate_row_count": None,
                    "raw_vector_payload_estimate_bytes": None,
                    "estimate_kind": None,
                }
                vector_cols.append(vc)
            metrics["vector_columns"] = vector_cols

            ms = _run_metric(cur, "relation_sizes", _DB_QUERIES["relation_sizes"])
            metrics["metric_status"]["relation_sizes"] = ms["status"]
            relations = []
            for row in ms["rows"]:
                rows_cnt = int(row[2]) if row[2] is not None else 0
                total_b = int(row[7]) if row[7] is not None else 0
                avg_bytes = None
                if rows_cnt > 0 and total_b > 0:
                    avg_bytes = round(total_b / rows_cnt)
                relations.append({
                    "schema_name": row[0],
                    "table_name": row[1],
                    "approximate_row_count": rows_cnt if rows_cnt else None,
                    "main_fork_bytes": int(row[3]) if row[3] is not None else 0,
                    "table_bytes": int(row[4]) if row[4] is not None else 0,
                    "toast_total_bytes": int(row[5]) if row[5] is not None else 0,
                    "indexes_bytes": int(row[6]) if row[6] is not None else 0,
                    "total_bytes": total_b,
                    "avg_total_bytes_per_estimated_row": avg_bytes,
                })
            metrics["relations"] = relations
            metrics["row_count_kind"] = "estimated"

            ms = _run_metric(cur, "index_details", _DB_QUERIES["index_details"])
            metrics["metric_status"]["index_details"] = ms["status"]
            index_details = []
            for row in ms["rows"]:
                am = row[4].lower() if row[4] else ""
                index_details.append({
                    "schema_name": row[0],
                    "table_name": row[1],
                    "index_name": row[2],
                    "index_bytes": int(row[3]) if row[3] is not None else 0,
                    "access_method": am,
                    "is_vector_index": am in _VECTOR_ACCESS_METHODS,
                })
            metrics["index_details"] = index_details

            ms = _run_metric(cur, "dead_tuple_stats", _DB_QUERIES["dead_tuple_stats"])
            metrics["metric_status"]["dead_tuple_stats"] = ms["status"]
            dead_stats = []
            for row in ms["rows"]:
                dead_stats.append({
                    "schema_name": row[0],
                    "table_name": row[1],
                    "n_live_tup": int(row[2]) if row[2] is not None else 0,
                    "n_dead_tup": int(row[3]) if row[3] is not None else 0,
                    "last_analyze": str(row[4]) if row[4] is not None else None,
                    "last_autoanalyze": str(row[5]) if row[5] is not None else None,
                })
            metrics["dead_tuple_stats"] = dead_stats

            ms = _run_metric(cur, "schema_totals", _DB_QUERIES["schema_totals"])
            metrics["metric_status"]["schema_totals"] = ms["status"]
            schema_totals = []
            for row in ms["rows"]:
                schema_totals.append({
                    "schema_name": row[0],
                    "total_bytes": int(row[1]) if row[1] is not None else 0,
                })
            metrics["schema_totals"] = schema_totals

        _enrich_vector_columns(metrics)

    except Exception as exc:
        metrics["available"] = False
        metrics["read_only_verified"] = False
        metrics["error"] = {"code": "database_connection_failed", "error_type": type(exc).__name__}
        metrics["warnings"].append("database connection failed")
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
    return metrics


def _enrich_vector_columns(metrics: dict):
    rel_rows = {}
    for r in metrics.get("relations", []):
        key = (r["schema_name"], r["table_name"])
        rel_rows[key] = r.get("approximate_row_count")

    for vc in metrics.get("vector_columns", []):
        key = (vc["schema_name"], vc["table_name"])
        rows = rel_rows.get(key)
        vkind = vc["vector_kind"]
        dim = vc.get("declared_dimension")
        vc["approximate_row_count"] = rows
        if vkind == "sparsevec":
            vc["raw_vector_payload_estimate_bytes"] = None
            vc["estimate_kind"] = None
            metrics.setdefault("warnings", []).append(
                "sparsevec size estimation not supported"
            )
        elif vkind in _VECTOR_KINDS and rows and dim:
            bytes_per_component = _VECTOR_KINDS[vkind]
            estimate = rows * dim * bytes_per_component
            vc["raw_vector_payload_estimate_bytes"] = estimate
            vc["estimate_kind"] = "derived"
        else:
            vc["raw_vector_payload_estimate_bytes"] = None
            vc["estimate_kind"] = None
