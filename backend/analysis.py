"""Point-in-time January 2026 Elexon wind forecast evaluation."""

from __future__ import annotations

import json
import math
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

UTC = timezone.utc
LONDON = ZoneInfo("Europe/London")
DECISION_START = date(2026, 1, 1)
DECISION_DAYS = 31
FORECAST_INTERVAL_MINUTES = 60
ACTUAL_INTERVAL_MINUTES = 30
COMPARISON_INTERVAL_MINUTES = 60
N2EX_AUCTION_URL = "https://support.nordpoolgroup.com/support/solutions/articles/8000088463-about-the-n2ex-day-ahead-auction"
AUCTIONS: dict[str, dict[str, Any]] = {
    "gb_60m": {
        "id": "gb_60m",
        "venue": "EPEX SPOT",
        "marketLabel": "EPEX SPOT GB 60-minute day-ahead auction",
        "label": "EPEX SPOT GB 60-minute day-ahead auction",
        "cutoffLocalTime": "09:20",
        "contractResolution": "60 minutes",
        "contractResolutionMinutes": 60,
    },
    "gb_30m": {
        "id": "gb_30m",
        "venue": "EPEX SPOT",
        "marketLabel": "EPEX SPOT GB 30-minute day-ahead auction",
        "label": "EPEX SPOT GB 30-minute day-ahead auction",
        "cutoffLocalTime": "15:30",
        "contractResolution": "30 minutes",
        "contractResolutionMinutes": 30,
    },
}


def parse_utc(value: str) -> datetime:
    """Parse an ISO timestamp and normalize it to UTC; naive values are invalid."""
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"Expected timezone-aware timestamp, got {value!r}")
    return parsed.astimezone(UTC)


def _iso_utc(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _read_rows(directory: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(directory.glob("*.json")):
        with path.open(encoding="utf-8") as source:
            chunk = json.load(source)
        if not isinstance(chunk, list):
            raise ValueError(f"Expected a JSON array in {path.name}")
        rows.extend(row for row in chunk if isinstance(row, dict))
    if not rows:
        raise FileNotFoundError(f"No Elexon source records found in {directory}")
    return rows


def _number(value: Any, *, field: str, timestamp: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"Invalid {field} value at {timestamp}: {value!r}") from error
    if not math.isfinite(result):
        raise ValueError(f"Non-finite {field} value at {timestamp}")
    return result


def _metrics(rows: list[dict[str, Any]]) -> dict[str, float | int | None]:
    """Calculate all headline error metrics from the same matched observations."""
    if not rows:
        return {
            "validMatchedPairs": 0,
            "maeMw": None,
            "rmseMw": None,
            "meanBiasMw": None,
            "wapePct": None,
            "positiveErrorCount": 0,
            "negativeErrorCount": 0,
            "zeroErrorCount": 0,
            "minErrorMw": None,
            "maxErrorMw": None,
        }

    errors = [float(row["forecastMw"]) - float(row["actualMw"]) for row in rows]
    sum_absolute_error = sum(abs(error) for error in errors)
    sum_absolute_actual = sum(abs(float(row["actualMw"])) for row in rows)
    return {
        "validMatchedPairs": len(rows),
        "maeMw": sum_absolute_error / len(rows),
        "rmseMw": math.sqrt(sum(error * error for error in errors) / len(rows)),
        "meanBiasMw": sum(errors) / len(errors),
        "wapePct": (sum_absolute_error / sum_absolute_actual * 100) if sum_absolute_actual else None,
        "positiveErrorCount": sum(error > 0 for error in errors),
        "negativeErrorCount": sum(error < 0 for error in errors),
        "zeroErrorCount": sum(error == 0 for error in errors),
        "minErrorMw": min(errors),
        "maxErrorMw": max(errors),
    }


def _decision_cutoff(decision_date: date, auction: dict[str, Any]) -> datetime:
    hour, minute = (int(part) for part in auction["cutoffLocalTime"].split(":"))
    local = datetime.combine(decision_date, time(hour, minute), tzinfo=LONDON)
    return local.astimezone(UTC)


def _metrics_for_hour_slots(slots: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [slot for slot in slots if slot["forecastMw"] is not None and slot["actualMw"] is not None]


def build_analysis(data_root: Path, auction_id: str = "gb_30m") -> dict[str, Any]:
    """Evaluate January purchasing decisions against their following delivery days.

    WINDFOR is hourly average power in MW. FUELHH is half-hour average power in MW,
    so two equal-duration actual intervals are averaged to form each hourly actual.
    Forecast vintages at the selected cutoff are eligible (publishTime <= cutoff).
    """
    if auction_id not in AUCTIONS:
        raise ValueError(f"Unsupported auction scenario: {auction_id!r}")
    auction = AUCTIONS[auction_id]
    actual_rows = _read_rows(data_root / "raw" / "fuelhh")
    forecast_rows = _read_rows(data_root / "raw" / "windfor")

    expected: list[dict[str, Any]] = []
    expected_actual_starts: set[datetime] = set()
    forecasts: dict[datetime, dict[datetime, float]] = defaultdict(dict)
    actuals: dict[datetime, float] = {}
    forecast_duplicates = 0
    actual_duplicates = 0
    post_cutoff_records = 0

    for decision_offset in range(DECISION_DAYS):
        decision_date = DECISION_START + timedelta(days=decision_offset)
        delivery_date = decision_date + timedelta(days=1)
        cutoff = _decision_cutoff(decision_date, auction)
        delivery_start_local = datetime.combine(delivery_date, time.min, tzinfo=LONDON)
        delivery_start_utc = delivery_start_local.astimezone(UTC)

        for hour in range(24):
            start = delivery_start_utc + timedelta(hours=hour)
            expected.append({
                "decisionDate": decision_date,
                "deliveryDate": delivery_date,
                "cutoff": cutoff,
                "intervalStart": start,
                "intervalEnd": start + timedelta(hours=1),
                "actualStarts": (start, start + timedelta(minutes=30)),
            })
            expected_actual_starts.update((start, start + timedelta(minutes=30)))

    expected_starts = {slot["intervalStart"] for slot in expected}

    for row in actual_rows:
        if row.get("fuelType") != "WIND" or not row.get("startTime"):
            continue
        timestamp = parse_utc(row["startTime"])
        if timestamp not in expected_actual_starts:
            continue
        generation = _number(row.get("generation"), field="FUELHH generation", timestamp=row["startTime"])
        previous = actuals.get(timestamp)
        if previous is not None:
            if previous != generation:
                raise ValueError(f"Conflicting FUELHH values at {timestamp.isoformat()}")
            actual_duplicates += 1
        else:
            actuals[timestamp] = generation

    for row in forecast_rows:
        if not row.get("startTime") or not row.get("publishTime"):
            continue
        start = parse_utc(row["startTime"])
        if start not in expected_starts:
            continue
        published = parse_utc(row["publishTime"])
        generation = _number(row.get("generation"), field="WINDFOR generation", timestamp=row["startTime"])
        previous = forecasts[start].get(published)
        if previous is not None:
            if previous != generation:
                raise ValueError(
                    f"Conflicting WINDFOR values for {start.isoformat()} published {published.isoformat()}"
                )
            forecast_duplicates += 1
        else:
            forecasts[start][published] = generation

    daily_slots: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in expected:
        decision_date: date = item["decisionDate"]
        delivery_date: date = item["deliveryDate"]
        cutoff: datetime = item["cutoff"]
        start: datetime = item["intervalStart"]
        actual_values = [actuals.get(actual_start) for actual_start in item["actualStarts"]]

        versions = forecasts.get(start, {})
        eligible_times = [published for published in versions if published <= cutoff]
        latest_eligible = max(eligible_times) if eligible_times else None
        if any(published > cutoff for published in versions):
            post_cutoff_records += sum(published > cutoff for published in versions)

        forecast_mw = versions[latest_eligible] if latest_eligible is not None else None
        actual_mw = (
            (actual_values[0] + actual_values[1]) / 2
            if all(value is not None for value in actual_values)
            else None
        )
        matched = forecast_mw is not None and actual_mw is not None
        slot = {
            "decisionDate": decision_date.isoformat(),
            "deliveryDate": delivery_date.isoformat(),
            "decisionCutoffUtc": _iso_utc(cutoff),
            "decisionCutoffLocal": cutoff.astimezone(LONDON).isoformat(),
            "intervalStart": _iso_utc(start),
            "intervalEnd": _iso_utc(item["intervalEnd"]),
            "forecastPublishTime": _iso_utc(latest_eligible) if latest_eligible else None,
            "forecastLeadMinutes": int((start - latest_eligible).total_seconds() / 60) if latest_eligible else None,
            "forecastAgeAtCutoffMinutes": int((cutoff - latest_eligible).total_seconds() / 60) if latest_eligible else None,
            "eligibleForecastVersions": len(eligible_times),
            "forecastMw": forecast_mw,
            "actualMw": actual_mw,
            "actualHalfHourValuesMw": actual_values,
            "actualHalfHoursAvailable": sum(value is not None for value in actual_values),
            "validMatched": matched,
            "errorMw": (forecast_mw - actual_mw) if matched else None,
            "absoluteErrorMw": abs(forecast_mw - actual_mw) if matched else None,
        }
        daily_slots[slot["decisionDate"]].append(slot)

    daily: list[dict[str, Any]] = []
    for decision_offset in range(DECISION_DAYS):
        decision_date = DECISION_START + timedelta(days=decision_offset)
        delivery_date = decision_date + timedelta(days=1)
        day_slots = daily_slots[decision_date.isoformat()]
        matched_rows = _metrics_for_hour_slots(day_slots)
        day_forecast_times = sorted({row["forecastPublishTime"] for row in day_slots if row["forecastPublishTime"]})
        eligible_count = sum(row["forecastPublishTime"] is not None for row in day_slots)
        actual_interval_count = sum(row["actualHalfHoursAvailable"] == 2 for row in day_slots)
        actual_half_hours = sum(row["actualHalfHoursAvailable"] for row in day_slots)
        daily.append({
            "decisionDate": decision_date.isoformat(),
            "deliveryDate": delivery_date.isoformat(),
            "expectedIntervals": len(day_slots),
            "eligibleForecastIntervals": eligible_count,
            "availableActualIntervals": actual_interval_count,
            "availableActualHalfHours": actual_half_hours,
            "validMatchedPairs": len(matched_rows),
            "missingEligibleForecastIntervals": len(day_slots) - eligible_count,
            "missingActualIntervals": len(day_slots) - actual_interval_count,
            "coveragePct": len(matched_rows) / len(day_slots) * 100 if day_slots else 0,
            "forecastPublishTimes": day_forecast_times,
            "complete": len(matched_rows) == len(day_slots),
            **_metrics(matched_rows),
        })

    all_slots = [slot for day in daily for slot in daily_slots[day["decisionDate"]]]
    matched_rows = _metrics_for_hour_slots(all_slots)
    eligible_count = sum(row["forecastPublishTime"] is not None for row in all_slots)
    actual_interval_count = sum(row["actualHalfHoursAvailable"] == 2 for row in all_slots)
    actual_half_hours = sum(row["actualHalfHoursAvailable"] for row in all_slots)

    manifest_path = data_root / "raw" / "manifest.json"
    retrieved_at = None
    forecast_publication_window = None
    if manifest_path.exists():
        with manifest_path.open(encoding="utf-8") as source:
            manifest = json.load(source)
        retrieved_at = manifest.get("updatedAtUtc") or manifest.get("retrievedAtUtc")
        forecast_requests = [request for request in manifest.get("requests", []) if request.get("dataset") == "WINDFOR"]
        if forecast_requests:
            forecast_publication_window = {
                "startUtc": min(request["from"] for request in forecast_requests),
                "endUtc": max(request["to"] for request in forecast_requests),
                "requestCount": len(forecast_requests),
                "windowing": manifest.get("queryWindowing"),
            }

    decision_end = DECISION_START + timedelta(days=DECISION_DAYS - 1)
    delivery_start = DECISION_START + timedelta(days=1)
    delivery_end = decision_end + timedelta(days=1)
    expected_interval_count = DECISION_DAYS * 24
    expected_actual_count = expected_interval_count * 2
    cutoff_examples = {
        key: value["cutoffLocalTime"] for key, value in AUCTIONS.items()
    }

    return {
        "period": {
            "decisionStart": DECISION_START.isoformat(),
            "decisionEnd": decision_end.isoformat(),
            "deliveryStart": delivery_start.isoformat(),
            "deliveryEnd": delivery_end.isoformat(),
            "timezone": "Europe/London",
        },
        "auction": {
            **auction,
            "cutoffTimezone": "Europe/London",
            "cutoffInclusive": True,
            "cutoffInterpretation": "Published EPEX SPOT local auction time used as a prototype replay cutoff; this is not a verified decision deadline for every buyer.",
            "allSupportedCutoffs": cutoff_examples,
            "referenceUrl": "https://www.epexspot.com/sites/default/files/2025-02/EPEX%20SPOT%20Trading%20Brochure%202025%20February.pdf",
            "n2exReferenceUrl": N2EX_AUCTION_URL,
            "n2exNote": "N2EX is a separate Nord Pool UK day-ahead auction for hourly curve orders, with a 09:50 GMT gate closure; it is not one of the EPEX scenarios in this replay.",
        },
        "resolution": {
            "forecastIntervalMinutes": FORECAST_INTERVAL_MINUTES,
            "actualIntervalMinutes": ACTUAL_INTERVAL_MINUTES,
            "comparisonIntervalMinutes": COMPARISON_INTERVAL_MINUTES,
            "comparisonIntervalsPerDeliveryDate": 24,
            "contractResolutionMinutes": auction["contractResolutionMinutes"],
            "contractResolutionMeasured": auction["contractResolutionMinutes"] == COMPARISON_INTERVAL_MINUTES,
            "limitation": (
                "WINDFOR is hourly, so the 30-minute EPEX scenario is evaluated as hourly source-series comparisons. This data cannot measure 30-minute forecast accuracy."
                if auction["contractResolutionMinutes"] == 30
                else "The 60-minute EPEX product matches the hourly comparison grain; FUELHH actuals are aggregated from two half-hour average-MW records."
            ),
        },
        "metrics": _metrics(matched_rows),
        "coverage": {
            "expectedIntervals": expected_interval_count,
            "eligibleForecastIntervals": eligible_count,
            "availableActualIntervals": actual_interval_count,
            "expectedActualHalfHours": expected_actual_count,
            "availableActualHalfHours": actual_half_hours,
            "missingActualHalfHours": expected_actual_count - actual_half_hours,
            "validMatchedPairs": len(matched_rows),
            "missingEligibleForecastIntervals": expected_interval_count - eligible_count,
            "missingActualIntervals": expected_interval_count - actual_interval_count,
            "coveragePct": len(matched_rows) / expected_interval_count * 100,
            "postCutoffForecastRecordsExcluded": post_cutoff_records,
            "identicalActualDuplicatesCollapsed": actual_duplicates,
            "identicalForecastDuplicatesCollapsed": forecast_duplicates,
        },
        "method": {
            "decisionRule": "January decision date D maps to the following local delivery date D+1.",
            "selectionRule": "For each hourly delivery interval, choose the latest WINDFOR publishTime <= the selected local auction cutoff.",
            "exactCutoffRule": "A forecast stamped exactly at the cutoff is eligible; all later publications are excluded.",
            "actualAggregation": "WINDFOR is hourly average MW. FUELHH is half-hour average MW; the two equal-duration half-hour averages are arithmetically averaged for each matching clock hour.",
            "sourceResolutionNote": "WINDFOR records in the included snapshot have hourly startTime values and Elexon documents an hourly wind forecast. FUELHH records are half-hour average MW. The 30-minute auction scenario does not support a half-hour forecast accuracy claim from these sources.",
            "marketScenarioNote": "EPEX SPOT documents GB 60-minute and 30-minute local day-ahead auction times at 09:20 and 15:30 GMT; this replay uses those times as prototype cutoffs. N2EX is a separate hourly UK day-ahead auction with a documented 09:50 GMT gate closure and is not modeled here.",
            "errorDefinition": "Forecast MW minus aligned actual MW; positive mean bias indicates forecast values above actual values.",
            "maeDefinition": "Mean absolute error over valid matched hourly pairs, in MW.",
            "rmseDefinition": "Square root of mean squared error over valid matched hourly pairs, in MW.",
            "biasDefinition": "Mean signed forecast-minus-actual error over valid matched hourly pairs, in MW.",
            "wapeDefinition": "Sum of absolute errors divided by sum of absolute actual MW, multiplied by 100.",
            "coverageDefinition": "Valid matched hourly pairs divided by 744 expected hourly intervals (31 decision dates × 24 hours).",
            "postCutoffExclusionDefinition": "Distinct WINDFOR (startTime, publishTime) versions after identical duplicate collapse, for the 744 expected hourly D+1 delivery starts, where publishTime is later than that interval's decision-date cutoff. The count is limited to the archived WINDFOR publication-time query windows in sources.forecastPublicationQueryWindow.",
        },
        "sources": {
            "actualDataset": "FUELHH, fuelType=WIND",
            "actualUrl": "https://data.elexon.co.uk/bmrs/api/v1/datasets/FUELHH/stream",
            "actualDescription": "Half-hourly average generation by fuel type, in MW.",
            "forecastDataset": "WINDFOR",
            "forecastUrl": "https://data.elexon.co.uk/bmrs/api/v1/datasets/WINDFOR/stream",
            "forecastDescription": "Hourly wind-generation forecast in MW for Power Park Modules visible to ESO with operational metering.",
            "scopeComparable": False,
            "scopeWarning": "Elexon describes WINDFOR as forecasts for wind farms visible to ESO with operational metering and FUELHH as fuel-type outturn. The exact asset populations are not demonstrated to be identical here; metrics are errors between these source series, not definitive total-national forecast errors.",
            "retrievedAtUtc": retrieved_at,
            "forecastPublicationQueryWindow": forecast_publication_window,
            "rawForecastRows": len(forecast_rows),
            "rawActualRows": len(actual_rows),
        },
        "daily": daily,
        "hourly": all_slots,
    }
