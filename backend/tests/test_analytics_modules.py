"""
Unit tests for individual analytics modules.

Each module exposes a single `run(params, filters, db)` coroutine.
Tests cover:
  - Missing year/month returns []
  - Happy path: DB returns rows → correct dict structure
  - Edge cases specific to each module (div-by-zero guards, label maps, etc.)
"""
from unittest.mock import AsyncMock, MagicMock

import pytest


def _mock_db(*rows) -> AsyncMock:
    """Return a mock AsyncSession whose execute() yields the given rows."""
    db = AsyncMock()
    result = MagicMock()
    result.fetchall.return_value = list(rows)
    result.fetchone.return_value = rows[0] if rows else None
    db.execute.return_value = result
    return db


def _row(**kwargs):
    """Create a mock row with named attributes."""
    r = MagicMock()
    for k, v in kwargs.items():
        setattr(r, k, v)
    return r


# ---------------------------------------------------------------------------
# trip_count_by_hour
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_trip_count_by_hour_no_params():
    from app.analytics.trip_count_by_hour import run
    assert await run({}, {}, AsyncMock()) == []


@pytest.mark.asyncio
async def test_trip_count_by_hour_returns_rows():
    from app.analytics.trip_count_by_hour import run
    db = _mock_db(_row(hour=9, trips=1500), _row(hour=10, trips=2000))
    result = await run({"year": 2024, "month": 1}, {}, db)
    assert result == [{"hour": 9, "trips": 1500}, {"hour": 10, "trips": 2000}]


@pytest.mark.asyncio
async def test_trip_count_by_hour_only_year_returns_empty():
    from app.analytics.trip_count_by_hour import run
    assert await run({"year": 2024}, {}, AsyncMock()) == []


# ---------------------------------------------------------------------------
# fare_vs_distance
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_fare_vs_distance_no_params():
    from app.analytics.fare_vs_distance import run
    assert await run({}, {}, AsyncMock()) == []


@pytest.mark.asyncio
async def test_fare_vs_distance_marks_outliers():
    from collections import namedtuple
    from app.analytics.fare_vs_distance import run

    # fare_vs_distance builds a DataFrame with pd.DataFrame(rows, columns=[...])
    # so rows must be iterable sequences, not attribute-only mocks.
    Row = namedtuple("Row", ["trip_distance", "fare_amount"])
    rows = [Row(trip_distance=1.0, fare_amount=float(f)) for f in [10, 11, 10, 12, 10, 500]]
    db = _mock_db(*rows)
    result = await run({"year": 2024, "month": 1}, {}, db)

    assert all("is_outlier" in r for r in result)
    # The $500 fare should be flagged
    assert any(r["fare_amount"] == 500 and r["is_outlier"] for r in result)
    # A normal $10 fare should not
    assert any(r["fare_amount"] == 10 and not r["is_outlier"] for r in result)


# ---------------------------------------------------------------------------
# top_pickup_zones
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_top_pickup_zones_no_params():
    from app.analytics.top_pickup_zones import run
    assert await run({}, {}, AsyncMock()) == []


@pytest.mark.asyncio
async def test_top_pickup_zones_returns_rows():
    from app.analytics.top_pickup_zones import run
    db = _mock_db(
        _row(zone="Midtown Center", borough="Manhattan", trips=5000),
        _row(zone="JFK Airport", borough="Queens", trips=3000),
    )
    result = await run({"year": 2024, "month": 1}, {}, db)
    assert result[0] == {"zone": "Midtown Center", "borough": "Manhattan", "trips": 5000}
    assert result[1] == {"zone": "JFK Airport", "borough": "Queens", "trips": 3000}


# ---------------------------------------------------------------------------
# tip_rate_by_payment
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_tip_rate_no_params():
    from app.analytics.tip_rate_by_payment import run
    assert await run({}, {}, AsyncMock()) == []


@pytest.mark.asyncio
async def test_tip_rate_labels_known_payment_type():
    from app.analytics.tip_rate_by_payment import run, PAYMENT_LABELS
    db = _mock_db(
        _row(payment_type=1, trips=100, avg_tip_pct=18.5, avg_tip_usd=2.5),
        _row(payment_type=2, trips=50, avg_tip_pct=None, avg_tip_usd=None),
    )
    result = await run({"year": 2024, "month": 1}, {}, db)
    assert result[0]["label"] == PAYMENT_LABELS[1]   # Credit Card
    assert result[0]["avg_tip_pct"] == 18.5
    assert result[1]["label"] == PAYMENT_LABELS[2]   # Cash
    # None values coerced to 0
    assert result[1]["avg_tip_pct"] == 0
    assert result[1]["avg_tip_usd"] == 0


@pytest.mark.asyncio
async def test_tip_rate_unknown_payment_type_labeled_other():
    from app.analytics.tip_rate_by_payment import run
    db = _mock_db(_row(payment_type=99, trips=5, avg_tip_pct=0.0, avg_tip_usd=0.0))
    result = await run({"year": 2024, "month": 1}, {}, db)
    assert result[0]["label"] == "Other"


# ---------------------------------------------------------------------------
# dow_revenue_heatmap
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_dow_revenue_no_params():
    from app.analytics.dow_revenue_heatmap import run
    assert await run({}, {}, AsyncMock()) == []


@pytest.mark.asyncio
async def test_dow_revenue_attaches_label():
    from app.analytics.dow_revenue_heatmap import run, DOW_LABELS
    db = _mock_db(_row(dow=1, hour=8, revenue=12345.67))
    result = await run({"year": 2024, "month": 1}, {}, db)
    assert result[0]["dow_label"] == DOW_LABELS[1]  # "Mon"
    assert result[0]["revenue"] == 12345.67


# ---------------------------------------------------------------------------
# avg_speed_by_hour
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_avg_speed_no_params():
    from app.analytics.avg_speed_by_hour import run
    assert await run({}, {}, AsyncMock()) == []


@pytest.mark.asyncio
async def test_avg_speed_returns_rows():
    from app.analytics.avg_speed_by_hour import run
    db = _mock_db(_row(hour=14, avg_mph=18.4, trips=3200))
    result = await run({"year": 2024, "month": 1}, {}, db)
    assert result == [{"hour": 14, "avg_mph": 18.4, "trips": 3200}]


# ---------------------------------------------------------------------------
# congestion_trend
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_congestion_trend_no_data():
    from app.analytics.congestion_trend import run
    db = _mock_db()  # empty fetchall
    result = await run({"year": 2024, "month": 1}, {}, db)
    assert result == []


@pytest.mark.asyncio
async def test_congestion_trend_coerces_none():
    from app.analytics.congestion_trend import run
    from datetime import date

    row = _row(
        data_month=date(2024, 1, 1),
        avg_congestion=None,
        total_congestion=None,
        trips=1000,
        pct_charged=None,
    )
    db = _mock_db(row)
    result = await run({}, {}, db)
    assert result[0]["avg_congestion"] == 0
    assert result[0]["total_congestion"] == 0
    assert result[0]["pct_charged"] == 0.0


@pytest.mark.asyncio
async def test_congestion_trend_pct_scaling():
    from app.analytics.congestion_trend import run
    from datetime import date

    row = _row(
        data_month=date(2024, 1, 1),
        avg_congestion=2.5,
        total_congestion=50000.0,
        trips=10000,
        pct_charged=0.75,  # stored as fraction, returned as percentage
    )
    db = _mock_db(row)
    result = await run({}, {}, db)
    assert result[0]["pct_charged"] == 75.0


# ---------------------------------------------------------------------------
# anomaly_flags
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_anomaly_flags_no_params():
    from app.analytics.anomaly_flags import run
    assert await run({}, {}, AsyncMock()) == []


@pytest.mark.asyncio
async def test_anomaly_flags_returns_correct_structure():
    from app.analytics.anomaly_flags import run

    row = _row(
        total_trips=10000,
        zero_distance=200,
        negative_fare=5,
        negative_total=3,
        sub_1min_trips=100,
        zero_passengers=50,
        extreme_distance=10,
        extreme_fare=2,
    )
    # fetchone-based: wire fetchone, not fetchall
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.fetchone.return_value = row
    db.execute.return_value = mock_result

    result = await run({"year": 2024, "month": 1}, {}, db)

    assert isinstance(result, list)
    keys = {r["anomaly"] for r in result}
    assert "Zero distance" in keys
    assert "Negative fare" in keys
    assert "Extreme fare (>$500)" in keys

    # Percentage check: zero_distance = 200 / 10000 * 100 = 2.0%
    zero_dist = next(r for r in result if r["anomaly"] == "Zero distance")
    assert zero_dist["pct"] == 2.0


@pytest.mark.asyncio
async def test_anomaly_flags_no_rows_returns_empty():
    from app.analytics.anomaly_flags import run

    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.fetchone.return_value = None
    db.execute.return_value = mock_result

    result = await run({"year": 2024, "month": 1}, {}, db)
    assert result == []
