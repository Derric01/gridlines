import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import app
from backend.analysis import _metrics, build_analysis

ROOT = Path(__file__).resolve().parents[1]


def _actual(start_time: str, generation: float, fuel_type: str = "WIND") -> dict:
    return {"startTime": start_time, "generation": generation, "fuelType": fuel_type}


def _forecast(start_time: str, publish_time: str, generation: float) -> dict:
    return {"startTime": start_time, "publishTime": publish_time, "generation": generation}


def _write_fixture(tmp_path: Path, actuals: list[dict], forecasts: list[dict]) -> Path:
    raw = tmp_path / "raw"
    (raw / "fuelhh").mkdir(parents=True)
    (raw / "windfor").mkdir(parents=True)
    (raw / "fuelhh" / "fixture.json").write_text(json.dumps(actuals), encoding="utf-8")
    (raw / "windfor" / "fixture.json").write_text(json.dumps(forecasts), encoding="utf-8")
    (raw / "manifest.json").write_text(json.dumps({"retrievedAtUtc": "test fixture"}), encoding="utf-8")
    return tmp_path


def _first_interval_fixture(tmp_path: Path, forecasts: list[dict], actuals: list[dict] | None = None) -> Path:
    if actuals is None:
        actuals = [
            _actual("2026-01-02T00:30:00Z", 30),
            _actual("2026-01-02T00:00:00Z", 10),
        ]
    return _write_fixture(tmp_path, actuals, forecasts)


def test_january_decisions_map_to_following_delivery_dates_including_month_boundary():
    result = build_analysis(ROOT / "data")
    first = result["hourly"][0]
    final = result["hourly"][-1]

    assert (first["decisionDate"], first["deliveryDate"]) == ("2026-01-01", "2026-01-02")
    assert (final["decisionDate"], final["deliveryDate"]) == ("2026-01-31", "2026-02-01")
    assert result["period"]["deliveryStart"] == "2026-01-02"
    assert result["period"]["deliveryEnd"] == "2026-02-01"


def test_real_elexon_snapshot_has_explicit_complete_hourly_coverage():
    result = build_analysis(ROOT / "data", "gb_30m")
    coverage = result["coverage"]

    assert coverage["expectedIntervals"] == 744
    assert coverage["eligibleForecastIntervals"] == 744
    assert coverage["availableActualHalfHours"] == 1488
    assert coverage["validMatchedPairs"] == 744
    assert coverage["missingEligibleForecastIntervals"] == 0
    assert coverage["missingActualIntervals"] == 0
    assert coverage["coveragePct"] == 100
    assert result["hourly"][-1]["forecastPublishTime"] == "2026-01-31T15:30:00Z"


def test_real_snapshot_resolution_is_hourly_forecast_and_half_hour_actual():
    forecast_rows = []
    for path in (ROOT / "data" / "raw" / "windfor").glob("*.json"):
        forecast_rows.extend(json.loads(path.read_text(encoding="utf-8")))
    actual_rows = []
    for path in (ROOT / "data" / "raw" / "fuelhh").glob("*.json"):
        actual_rows.extend(json.loads(path.read_text(encoding="utf-8")))
    wind_actuals = [row for row in actual_rows if row.get("fuelType") == "WIND"]

    assert {row["startTime"][14:16] for row in forecast_rows} == {"00"}
    assert {row["startTime"][14:16] for row in wind_actuals} == {"00", "30"}

    half_hour_auction = build_analysis(ROOT / "data", "gb_30m")
    hourly_auction = build_analysis(ROOT / "data", "gb_60m")
    assert half_hour_auction["resolution"]["forecastIntervalMinutes"] == 60
    assert half_hour_auction["resolution"]["actualIntervalMinutes"] == 30
    assert half_hour_auction["resolution"]["comparisonIntervalMinutes"] == 60
    assert half_hour_auction["resolution"]["contractResolutionMeasured"] is False
    assert len(half_hour_auction["hourly"]) == 31 * 24
    assert half_hour_auction["coverage"]["expectedActualHalfHours"] == 31 * 48
    assert hourly_auction["resolution"]["contractResolutionMeasured"] is True
    assert hourly_auction["auction"]["marketLabel"].startswith("EPEX SPOT GB 60-minute")


def test_latest_vintage_at_exact_cutoff_is_included_and_later_vintage_excluded(tmp_path: Path):
    result = build_analysis(_first_interval_fixture(tmp_path, [
        _forecast("2026-01-02T00:00:00Z", "2026-01-01T11:30:00Z", 20),
        _forecast("2026-01-02T00:00:00Z", "2026-01-01T15:30:00Z", 30),
        _forecast("2026-01-02T00:00:00Z", "2026-01-01T15:30:01Z", 300),
    ]))
    first = result["hourly"][0]

    assert first["decisionCutoffUtc"] == "2026-01-01T15:30:00Z"
    assert first["decisionCutoffLocal"] == "2026-01-01T15:30:00+00:00"
    assert first["forecastPublishTime"] == "2026-01-01T15:30:00Z"
    assert first["forecastMw"] == 30
    assert first["actualMw"] == 20
    assert first["errorMw"] == 10


def test_sixty_minute_auction_uses_its_own_cutoff_and_never_uses_later_vintage(tmp_path: Path):
    result = build_analysis(_first_interval_fixture(tmp_path, [
        _forecast("2026-01-02T00:00:00Z", "2026-01-01T08:30:00Z", 10),
        _forecast("2026-01-02T00:00:00Z", "2026-01-01T09:20:00Z", 20),
        _forecast("2026-01-02T00:00:00Z", "2026-01-01T09:20:01Z", 100),
    ]), "gb_60m")
    first = result["hourly"][0]

    assert result["auction"]["cutoffLocalTime"] == "09:20"
    assert first["decisionCutoffUtc"] == "2026-01-01T09:20:00Z"
    assert first["forecastPublishTime"] == "2026-01-01T09:20:00Z"
    assert first["forecastMw"] == 20


def test_missing_eligible_forecast_remains_missing_even_if_later_records_exist(tmp_path: Path):
    result = build_analysis(_first_interval_fixture(tmp_path, [
        _forecast("2026-01-02T00:00:00Z", "2026-01-01T15:30:01Z", 500),
    ]))

    assert result["hourly"][0]["forecastMw"] is None
    assert result["hourly"][0]["validMatched"] is False
    assert result["coverage"]["eligibleForecastIntervals"] == 0
    assert result["coverage"]["missingEligibleForecastIntervals"] == 744
    assert result["metrics"]["maeMw"] is None


def test_actuals_are_aligned_by_timestamp_and_equal_duration_mw_values_are_averaged(tmp_path: Path):
    result = build_analysis(_first_interval_fixture(tmp_path, [
        _forecast("2026-01-02T00:00:00Z", "2026-01-01T15:30:00Z", 20),
    ], actuals=[
        _actual("2026-01-02T00:30:00Z", 30),
        _actual("2026-01-02T00:00:00Z", 10),
        _actual("2026-01-02T00:00:00Z", 900, fuel_type="SOLAR"),
    ]))
    first = result["hourly"][0]

    assert first["actualHalfHourValuesMw"] == [10, 30]
    assert first["actualMw"] == 20
    assert first["errorMw"] == 0
    assert first["actualHalfHoursAvailable"] == 2


def test_coverage_denominators_and_missing_actual_counts_are_timestamp_based(tmp_path: Path):
    result = build_analysis(_first_interval_fixture(tmp_path, [
        _forecast("2026-01-02T00:00:00Z", "2026-01-01T15:30:00Z", 20),
    ], actuals=[_actual("2026-01-02T00:00:00Z", 10)]))
    coverage = result["coverage"]

    assert coverage["expectedIntervals"] == 744
    assert coverage["eligibleForecastIntervals"] == 1
    assert coverage["availableActualHalfHours"] == 1
    assert coverage["availableActualIntervals"] == 0
    assert coverage["validMatchedPairs"] == 0
    assert coverage["missingEligibleForecastIntervals"] == 743
    assert coverage["missingActualIntervals"] == 744
    assert coverage["missingActualHalfHours"] == 1487


def test_metrics_match_hand_calculation_and_zero_denominator_is_null():
    rows = [
        {"forecastMw": 10, "actualMw": 7},
        {"forecastMw": 3, "actualMw": 7},
    ]
    metrics = _metrics(rows)

    assert metrics["validMatchedPairs"] == 2
    assert metrics["maeMw"] == pytest.approx(3.5)
    assert metrics["rmseMw"] == pytest.approx((12.5) ** 0.5)
    assert metrics["meanBiasMw"] == pytest.approx(-0.5)
    assert metrics["wapePct"] == pytest.approx(50)
    assert metrics["positiveErrorCount"] == 1
    assert metrics["negativeErrorCount"] == 1
    assert metrics["zeroErrorCount"] == 0
    assert metrics["minErrorMw"] == -4
    assert metrics["maxErrorMw"] == 3
    assert _metrics([{ "forecastMw": 0, "actualMw": 0 }])["wapePct"] is None
    assert _metrics([{ "forecastMw": 0, "actualMw": 0 }])["zeroErrorCount"] == 1
    assert _metrics([])["maeMw"] is None


def test_conflicting_duplicate_records_fail_deterministically(tmp_path: Path):
    source = _first_interval_fixture(tmp_path, [
        _forecast("2026-01-02T00:00:00Z", "2026-01-01T15:30:00Z", 20),
        _forecast("2026-01-02T00:00:00Z", "2026-01-01T15:30:00Z", 21),
    ])

    with pytest.raises(ValueError, match="Conflicting WINDFOR"):
        build_analysis(source)


def test_identical_duplicates_are_collapsed_and_scope_warning_is_explicit(tmp_path: Path):
    source = _first_interval_fixture(tmp_path, [
        _forecast("2026-01-02T00:00:00Z", "2026-01-01T15:30:00Z", 20),
        _forecast("2026-01-02T00:00:00Z", "2026-01-01T15:30:00Z", 20),
    ])
    result = build_analysis(source)

    assert result["coverage"]["identicalForecastDuplicatesCollapsed"] == 1
    assert result["sources"]["scopeComparable"] is False
    assert "not demonstrated to be identical" in result["sources"]["scopeWarning"]


def test_daily_monthly_api_metrics_and_missing_data_counts_share_one_aligned_set():
    client = TestClient(app)
    payload = client.get("/api/analysis?auction=gb_30m").json()

    assert payload["period"]["decisionStart"] == "2026-01-01"
    assert payload["period"]["deliveryStart"] == "2026-01-02"
    assert payload["period"]["deliveryEnd"] == "2026-02-01"
    assert payload["auction"]["marketLabel"].startswith("EPEX SPOT GB 30-minute")
    assert payload["auction"]["cutoffLocalTime"] == "15:30"
    assert payload["auction"]["cutoffTimezone"] == "Europe/London"
    assert "prototype replay cutoff" in payload["auction"]["cutoffInterpretation"]
    assert payload["resolution"]["comparisonIntervalMinutes"] == 60
    assert payload["resolution"]["contractResolutionMeasured"] is False
    assert payload["resolution"]["contractResolutionMinutes"] == 30
    assert "cannot measure 30-minute forecast accuracy" in payload["resolution"]["limitation"]
    assert "09:50 GMT" in payload["auction"]["n2exNote"]
    assert len(payload["daily"]) == 31
    assert len(payload["hourly"]) == 744
    assert payload["metrics"]["validMatchedPairs"] == sum(row["validMatched"] for row in payload["hourly"])
    assert payload["metrics"]["validMatchedPairs"] == sum(day["validMatchedPairs"] for day in payload["daily"])
    assert payload["coverage"]["validMatchedPairs"] == payload["metrics"]["validMatchedPairs"]
    matched = [row for row in payload["hourly"] if row["validMatched"]]
    errors = [row["errorMw"] for row in matched]
    actuals = [row["actualMw"] for row in matched]
    assert payload["metrics"]["maeMw"] == pytest.approx(sum(abs(error) for error in errors) / len(errors))
    assert payload["metrics"]["rmseMw"] == pytest.approx((sum(error ** 2 for error in errors) / len(errors)) ** 0.5)
    assert payload["metrics"]["meanBiasMw"] == pytest.approx(sum(errors) / len(errors))
    assert payload["metrics"]["wapePct"] == pytest.approx(sum(abs(error) for error in errors) / sum(abs(value) for value in actuals) * 100)
    for day in payload["daily"]:
        daily_rows = [row for row in matched if row["decisionDate"] == day["decisionDate"]]
        daily_errors = [row["errorMw"] for row in daily_rows]
        daily_actuals = [row["actualMw"] for row in daily_rows]
        assert day["validMatchedPairs"] == len(daily_rows)
        assert day["maeMw"] == pytest.approx(sum(abs(error) for error in daily_errors) / len(daily_errors))
        assert day["rmseMw"] == pytest.approx((sum(error ** 2 for error in daily_errors) / len(daily_errors)) ** 0.5)
        assert day["meanBiasMw"] == pytest.approx(sum(daily_errors) / len(daily_errors))
        assert day["wapePct"] == pytest.approx(sum(abs(error) for error in daily_errors) / sum(abs(value) for value in daily_actuals) * 100)
    assert payload["sources"]["scopeComparable"] is False
    assert client.get("/api/analysis?auction=invalid").status_code == 422


def test_real_snapshot_signed_error_counts_and_positive_only_days_are_reproducible():
    expected = {
        "gb_30m": {"positive": 653, "negative": 91, "zero": 0, "minimum": -2720, "maximum": 7073, "positiveOnlyDays": 18},
        "gb_60m": {"positive": 632, "negative": 112, "zero": 0, "minimum": -3550, "maximum": 6870, "positiveOnlyDays": 19},
    }
    for auction_id, expected_values in expected.items():
        result = build_analysis(ROOT / "data", auction_id)
        metrics = result["metrics"]
        matched_rows = [row for row in result["hourly"] if row["validMatched"]]
        assert len({row["intervalStart"] for row in matched_rows}) == metrics["validMatchedPairs"]
        assert len({row["forecastMw"] for row in matched_rows}) > 700
        assert all(row["forecastPublishTime"] <= row["decisionCutoffUtc"] for row in matched_rows)
        assert metrics["positiveErrorCount"] == expected_values["positive"]
        assert metrics["negativeErrorCount"] == expected_values["negative"]
        assert metrics["zeroErrorCount"] == expected_values["zero"]
        assert metrics["minErrorMw"] == expected_values["minimum"]
        assert metrics["maxErrorMw"] == expected_values["maximum"]
        assert metrics["positiveErrorCount"] + metrics["negativeErrorCount"] + metrics["zeroErrorCount"] == metrics["validMatchedPairs"]

        positive_only_days = 0
        for day in result["daily"]:
            rows = [row for row in result["hourly"] if row["decisionDate"] == day["decisionDate"] and row["validMatched"]]
            assert day["positiveErrorCount"] == sum(row["errorMw"] > 0 for row in rows)
            assert day["negativeErrorCount"] == sum(row["errorMw"] < 0 for row in rows)
            assert day["zeroErrorCount"] == sum(row["errorMw"] == 0 for row in rows)
            assert day["minErrorMw"] == min(row["errorMw"] for row in rows)
            assert day["maxErrorMw"] == max(row["errorMw"] for row in rows)
            if rows and day["negativeErrorCount"] == 0:
                positive_only_days += 1
                assert day["maeMw"] == pytest.approx(day["meanBiasMw"])
        assert positive_only_days == expected_values["positiveOnlyDays"]


def test_scenarios_select_different_archived_vintages_and_recompute_analysis_payloads():
    hourly = build_analysis(ROOT / "data", "gb_60m")
    half_hour = build_analysis(ROOT / "data", "gb_30m")

    assert hourly["auction"]["cutoffLocalTime"] == "09:20"
    assert half_hour["auction"]["cutoffLocalTime"] == "15:30"
    assert all(
        row["forecastPublishTime"] <= row["decisionCutoffUtc"]
        for result in (hourly, half_hour)
        for row in result["hourly"]
        if row["forecastPublishTime"]
    )
    assert all(
        left["forecastPublishTime"] != right["forecastPublishTime"]
        for left, right in zip(hourly["hourly"], half_hour["hourly"], strict=True)
    )
    assert all(
        left["forecastMw"] != right["forecastMw"]
        for left, right in zip(hourly["hourly"], half_hour["hourly"], strict=True)
    )
    assert hourly["metrics"] != half_hour["metrics"]
    assert [day["maeMw"] for day in hourly["daily"]] != [day["maeMw"] for day in half_hour["daily"]]

    manifest = json.loads((ROOT / "data" / "raw" / "manifest.json").read_text(encoding="utf-8"))
    forecast_requests = [request for request in manifest["requests"] if request["dataset"] == "WINDFOR"]
    for result in (hourly, half_hour):
        metrics = result["metrics"]
        assert metrics["positiveErrorCount"] + metrics["negativeErrorCount"] + metrics["zeroErrorCount"] == metrics["validMatchedPairs"]
        assert result["coverage"]["postCutoffForecastRecordsExcluded"] > 0
        query_window = result["sources"]["forecastPublicationQueryWindow"]
        assert query_window["startUtc"] == min(request["from"] for request in forecast_requests)
        assert query_window["endUtc"] == max(request["to"] for request in forecast_requests)


def test_api_health_docs_and_frontend_are_available():
    client = TestClient(app)

    assert client.get("/api/health").json() == {"status": "ok", "service": "gridline"}
    assert client.get("/api/docs").status_code == 200
    home = client.get("/")
    assert home.status_code == 200
    assert "Gridline" in home.text


def test_api_returns_clear_service_error_when_source_data_is_absent(monkeypatch):
    def missing_source(auction_id: str = "gb_30m"):
        raise FileNotFoundError("No Elexon source records found")

    monkeypatch.setattr("app.get_analysis", missing_source)
    response = TestClient(app).get("/api/analysis")

    assert response.status_code == 503
    assert "Analysis data unavailable" in response.json()["detail"]
