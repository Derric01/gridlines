# Gridline — short application walkthrough

Hi, I'm Derric. This is Gridline. Let me show you how I'd use it to check a wind forecast against what actually happened.

The dashboard covers decisions made during January twenty twenty-six. A decision on one day is matched with generation on the following day. Right now, the selected cutoff is three thirty in the afternoon, London time.

I'll pick the tenth of January. The delivery date changes to the eleventh. The green line is the forecast available at decision time. The dashed line is the actual generation. You can see that the forecast is consistently higher here.

If I open the values underneath, I can check the actual numbers and when that forecast was published. That publication time matters. A later revision can't be used to judge an earlier decision.

The monthly mean absolute error is about eighteen hundred and seventy-three megawatts, and the bias is positive. So in this snapshot, forecasts generally sit above the actuals. These are forecast-error measures, rather than a calculation of money saved.

To find the days worth investigating, I go to Daily accuracy. The tenth of January stands out, with an average error of roughly forty-eight hundred and eighty-one megawatts. I can open that row and go straight back to its chart. The date selection also handles the end of the month: the thirty-first of January maps to delivery on the first of February.

One detail I wanted to make clear is the time resolution. On Method and sources, you can see that the forecasts are hourly, while the actual observations are half-hourly. The app averages both half-hours for an hourly comparison. It doesn't measure half-hour forecast accuracy. The two datasets also aren't proven to cover exactly the same wind assets.

Underneath, it's a React frontend with a Fast A P I backend reading archived Elexon records. The important safeguard is selecting only forecast publications available by the cutoff. The existing Python and CSV checks passed during validation.

That's Gridline: I can start with the monthly picture, find a difficult day, and inspect the forecast and source details behind it.
