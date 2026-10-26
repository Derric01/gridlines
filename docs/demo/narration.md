# Gridline narration

Narration only. Microsoft Ravi · English (India) · synthetic catalog voice. No voice cloning.

## 00:00 — The problem

Hi, I'm Derric. This is Gridline, my historical wind forecast review project. For a UK electricity utility, purchasing decisions depend on expected demand and the generation likely to be available. Wind adds uncertainty, because the forecast can change before delivery. Gridline focuses on one part of that problem: looking back at the wind forecast available at a particular decision time, then comparing it with what was generated the following day. Let me walk through the application first, then the implementation.

## 00:41 — Dashboard and coverage

The dashboard covers purchasing decision dates from the first to the thirty-first of January, twenty twenty-six. Each decision maps to next-day delivery, so the delivery period runs from the second of January through the first of February. I'm using the EPEX thirty-minute auction scenario, with a fifteen-thirty London cutoff. The coverage panel shows seven hundred and forty-four matched hourly pairs, and all fourteen hundred and eighty-eight half-hour actual records. That tells us how much data supports the monthly figures.

## 01:20 — Forecast versus actual

Here, I can choose a decision date and inspect its following delivery day. The solid green line is the selected forecast, and the dashed line is actual generation. I'll open the tenth of January, which maps to delivery on the eleventh. The gap is visible across the day. The values table also exposes the publication time behind each forecast. That timestamp matters: a forecast published after the decision cutoff would give the analysis information the buyer didn't have. Gridline chooses the latest eligible publication for each hour. It doesn't use later revisions to make the historical result look better.

## 02:06 — What the metrics mean

The monthly mean absolute error is one thousand, eight hundred and seventy-three megawatts. That's the average size of the hourly difference, ignoring direction. Root mean squared error is two thousand, three hundred and twenty-seven megawatts; larger misses carry more weight in that measure. Mean bias is positive one thousand, seven hundred and nine megawatts, so this source forecast tends to sit above the aligned actuals. WAPE is sixteen point six percent: total absolute error divided by total absolute actual generation. These figures describe differences between the source series. They don't directly measure money saved or establish a purchasing strategy.

## 02:58 — Find the difficult days

The Daily accuracy page makes the monthly result easier to investigate. Each row keeps the decision date and delivery date together, alongside error measures and coverage. The tenth of January has a daily mean absolute error of about four thousand, eight hundred and eighty-one megawatts. The eighteenth is much lower, at about two hundred and fifty-two. Selecting a row returns to the corresponding hourly replay. I can then check whether the error was sustained or concentrated in particular hours, and whether missing data could have affected the comparison.

## 03:38 — Method and limitations

The Method and sources page explains the comparison. WINDFOR supplies hourly forecasts in average megawatts. FUELHH supplies half-hour actuals, so the application averages both equal-duration actual values for each hour. Both must exist. Even under the thirty-minute auction scenario, this remains an hourly comparison. There's also a scope limitation: the forecast and actual datasets aren't demonstrated to cover exactly the same wind assets. I keep that warning visible because complete coverage doesn't, by itself, prove that the populations are identical. The source links and snapshot details make those assumptions inspectable.

## 04:28 — Client takeaway

That's the client view: a way to move from monthly error, to a difficult delivery day, to the underlying forecast vintage. The value is being able to inspect the evidence and limitations together. Next, I'll show how the code preserves that historical decision boundary.

## 04:50 — Architecture

The frontend is React, built with Vite. In App dot J S X, changing the auction scenario requests the same-origin analysis endpoint. FastAPI defines that endpoint in app dot P Y and delegates the calculation to backend slash analysis dot P Y. The response contains monthly metrics, daily summaries, hourly observations, coverage, and methodology. The API caches the two scenario results. Locally, Vite proxies API requests to FastAPI; the production routing is configured separately.

## 05:24 — Archived source data

The repository includes archived Elexon JSON under data slash raw, plus a manifest recording query windows and retrieval metadata. This backend reads that snapshot; it doesn't download new Elexon data on every request. Actual records are filtered to fuel type WIND. Both series use startTime and generation; forecasts also use publishTime. Timestamps must include a timezone and are normalized to UTC. Numeric values must be finite. Identical duplicates are collapsed, while conflicting values for the same record identity raise an error. I didn't find a committed download implementation, so I'm not presenting one here.

## 06:06 — Point-in-time replay

The main safeguard is in forecast selection. For each expected delivery hour, the code collects publication times that are less than or equal to the decision cutoff, then selects the latest one. A publication exactly at cutoff is eligible. One second later is excluded. If no eligible version exists, the forecast stays missing; a later version cannot fill the gap. The decision-date loop constructs next-day delivery explicitly, including the thirty-first of January mapping to the first of February. London local cutoffs are converted to UTC before matching. The two scenarios change the decision boundary, rather than changing the source resolution.

## 06:47 — Alignment and metrics

For each hour, actual generation is the arithmetic mean of the observations at the hour and thirty minutes past. Those are equal-duration average-power readings, so their mean gives hourly average megawatts. If either reading is missing, the hourly actual is missing too. The metric function uses only rows with both a forecast and an actual value. It calculates signed forecast-minus-actual errors from unrounded inputs. Daily and monthly summaries use the same alignment. WAPE returns no value when its denominator is zero, rather than inventing a percentage. Missing observations remain visible in coverage.

## 07:26 — Validation

The Python tests cover the month boundary, exact-cutoff eligibility, later-publication exclusion, missing forecasts, actual alignment, conflicting duplicates, coverage, and hand-calculated metrics. They also exercise the API. After building the frontend, I ran the existing suite: all sixteen tests passed. The four frontend CSV tests passed as well, covering field mapping, missing values, escaping, and scenario-specific exports. The production frontend build also completed. These checks support the replay and export behavior; they don't establish that the source datasets contain identical assets, or that the application predicts financial outcomes.

## 08:11 — Docker and deployment

The Dockerfile uses a Node stage to build the frontend, then copies it into a Python runtime alongside FastAPI and the archived data. Docker Compose exposes the combined application on port eight thousand. The README documents that route and the separate development servers. Vercel uses a different arrangement: the configuration declares FastAPI and Vite services, routes API paths to the backend first, then routes other paths to the frontend. The deployed dashboard is accessible. I haven't launched Docker or performed a deployment during this review, so I'm describing the checked-in configuration, not claiming an additional deployment test.

## 08:51 — Engineering takeaway

The core of Gridline is a traceable comparison: archived source records, an explicit decision cutoff, next-day delivery, and metrics computed from aligned observations. The interface makes the selected forecast, coverage, and limitations visible together. Its boundaries are equally clear: hourly source resolution, uncertain population equivalence, and prototype auction-time cutoffs. Those are the points I'd validate before extending the analysis to procurement decisions. That completes the product demonstration and technical review. The screen content comes from the real application and repository; the narration is AI-assisted.
