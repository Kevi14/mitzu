"""
Shared filter-clause builder for analytics modules.

Usage:
    filter_sql, filter_params = build_filter_clause(filters, table_alias="t")
    query = text(SQL_TEMPLATE.format(filters=filter_sql))
    await db.execute(query, {"data_month": ..., **filter_params})

The SQL template should contain a `{filters}` placeholder inside a WHERE block.
When no filters are present, `filter_sql` is an empty string and nothing changes.
Column names and operators are strictly whitelisted; values are parameterized.
"""

FILTERABLE_COLUMNS = frozenset({
    "trip_distance",
    "fare_amount",
    "tip_amount",
    "total_amount",
    "passenger_count",
    "pu_location_id",
    "do_location_id",
    "payment_type",
    "rate_code_id",
    "congestion_surcharge",
    "airport_fee",
})

VALID_OPERATORS = frozenset({">", "<", ">=", "<=", "=", "!="})


def build_filter_clause(filters: dict, table_alias: str = "") -> tuple[str, dict]:
    """
    Returns (sql_fragment, bind_params).

    sql_fragment  — "" when empty, otherwise "AND col op :f_col [AND ...]"
    bind_params   — {"f_col": value, ...}
    """
    prefix = f"{table_alias}." if table_alias else ""
    clauses: list[str] = []
    bind_params: dict = {}

    for field, spec in (filters or {}).items():
        if field not in FILTERABLE_COLUMNS:
            continue
        operator = spec.get("operator", "=")
        if operator not in VALID_OPERATORS:
            continue
        value = spec.get("value")
        if value is None:
            continue
        try:
            value = float(value)
        except (TypeError, ValueError):
            pass
        param_name = f"f_{field}"
        clauses.append(f"{prefix}{field} {operator} :{param_name}")
        bind_params[param_name] = value

    if not clauses:
        return "", {}
    return "AND " + " AND ".join(clauses), bind_params
