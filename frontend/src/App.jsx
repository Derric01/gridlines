import { useEffect, useMemo, useRef, useState } from 'react';

import { createAnalysisCsv } from './csv.js';

const NAV_ITEMS = [
  { id: 'overview', label: 'Forecast review', icon: 'chart' },
  { id: 'accuracy', label: 'Daily accuracy', icon: 'calendar' },
  { id: 'sources', label: 'Method & sources', icon: 'layers' },
];

const AUCTION_OPTIONS = [
  { id: 'gb_30m', label: 'EPEX SPOT GB 30-minute · 15:30' },
  { id: 'gb_60m', label: 'EPEX SPOT GB 60-minute · 09:20' },
];

function Icon({ name, size = 18 }) {
  const paths = {
    chart: <><path d="M3 3v18h18" /><path d="m19 9-5 5-4-4-5 5" /></>,
    calendar: <><rect x="3" y="5" width="18" height="16" rx="2" /><path d="M16 3v4M8 3v4M3 10h18M8 14h.01M12 14h.01M16 14h.01M8 17h.01M12 17h.01" /></>,
    layers: <><path d="m12 3 9 5-9 5-9-5 9-5Z" /><path d="m3 12 9 5 9-5M3 16l9 5 9-5" /></>,
    sun: <><circle cx="12" cy="12" r="4" /><path d="M12 2v2m0 16v2M4.93 4.93l1.42 1.42m11.3 11.3 1.42 1.42M2 12h2m16 0h2M4.93 19.07l1.42-1.42m11.3-11.3 1.42-1.42" /></>,
    moon: <path d="M20.9 13A9 9 0 0 1 11 3.1 9 9 0 1 0 20.9 13Z" />,
    download: <><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><path d="m7 10 5 5 5-5M12 15V3" /></>,
    check: <path d="m5 12 4 4L19 6" />,
    arrow: <><path d="M7 17 17 7M7 7h10v10" /></>,
    info: <><circle cx="12" cy="12" r="10" /><path d="M12 16v-4M12 8h.01" /></>,
  };
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name]}</svg>;
}

function formatNumber(value, decimals = 0) {
  if (value === null || value === undefined || !Number.isFinite(Number(value))) return '—';
  return new Intl.NumberFormat('en-GB', { maximumFractionDigits: decimals, minimumFractionDigits: decimals }).format(value);
}

function signedNumber(value, decimals = 0) {
  return value > 0 ? '+' + formatNumber(value, decimals) : formatNumber(value, decimals);
}

function dateLabel(value, options = { day: 'numeric', month: 'short' }) {
  if (!value) return '—';
  return new Intl.DateTimeFormat('en-GB', { timeZone: 'UTC', ...options }).format(new Date(value + 'T12:00:00Z'));
}

function timeLabel(value) {
  if (!value) return '—';
  return new Intl.DateTimeFormat('en-GB', { timeZone: 'Europe/London', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' }).format(new Date(value));
}

function makePath(rows, key, plot) {
  let drawing = false;
  return rows.map((row, index) => {
    const value = row[key];
    if (value === null || value === undefined || !Number.isFinite(Number(value))) {
      drawing = false;
      return '';
    }
    const x = plot.left + (index / Math.max(1, rows.length - 1)) * plot.width;
    const y = plot.top + plot.height - (value / plot.maxY) * plot.height;
    const command = (drawing ? 'L' : 'M') + x.toFixed(2) + ',' + y.toFixed(2);
    drawing = true;
    return command;
  }).filter(Boolean).join(' ');
}

function HourlyChart({ rows, decisionDate, deliveryDate }) {
  const [showForecast, setShowForecast] = useState(true);
  const [showActual, setShowActual] = useState(true);
  const [chartWidth, setChartWidth] = useState(960);
  const chartRef = useRef(null);
  useEffect(() => {
    const chartElement = chartRef.current;
    if (!chartElement || !window.ResizeObserver) return undefined;
    const observer = new ResizeObserver(([entry]) => setChartWidth(Math.max(320, Math.round(entry.contentRect.width))));
    observer.observe(chartElement);
    return () => observer.disconnect();
  }, []);
  const compact = chartWidth < 560;
  const chartHeight = compact ? 220 : 292;
  const plot = { left: compact ? 46 : 56, top: 16, width: chartWidth - (compact ? 60 : 72), height: compact ? 158 : 232 };
  const finiteValues = rows.flatMap((row) => [row.forecastMw, row.actualMw]).filter((value) => Number.isFinite(value));
  const maxValue = Math.max(...finiteValues, 1);
  plot.maxY = Math.ceil(maxValue / 2000) * 2000 || 2000;
  const ticks = Array.from({ length: 5 }, (_, index) => (plot.maxY / 4) * index);
  const forecastPath = makePath(rows, 'forecastMw', plot);
  const actualPath = makePath(rows, 'actualMw', plot);
  const xForIndex = (index) => plot.left + (index / Math.max(1, rows.length - 1)) * plot.width;
  const yFor = (value) => plot.top + plot.height - (value / plot.maxY) * plot.height;

  return (
    <div className="chart-wrap">
      <svg ref={chartRef} className="hourly-chart" viewBox={'0 0 ' + chartWidth + ' ' + chartHeight} role="img" aria-labelledby="chart-title chart-description">
        <title id="chart-title">Wind forecast and actual for delivery on {dateLabel(deliveryDate, { day: 'numeric', month: 'long', year: 'numeric' })}</title>
        <desc id="chart-description">Hourly wind generation in megawatts. Forecast values are the latest records at or before the selected decision cutoff. Actual values are averages of both half-hour FUELHH records; gaps indicate missing source values.</desc>
        {ticks.map((tick) => {
          const y = yFor(tick);
          return <g key={tick}><line x1={plot.left} x2={plot.left + plot.width} y1={y} y2={y} className="chart-grid" /><text x={plot.left - 12} y={y + 4} className="axis-label" textAnchor="end">{formatNumber(tick)}</text></g>;
        })}
        {[0, 6, 12, 18, 23].map((hour) => {
          const x = xForIndex(hour);
          return <g key={hour}><line x1={x} x2={x} y1={plot.top + plot.height} y2={plot.top + plot.height + 4} className="axis-tick" /><text x={x} y={plot.top + plot.height + 24} className="axis-label" textAnchor={hour === 0 ? 'start' : hour === 23 ? 'end' : 'middle'}>{String(hour).padStart(2, '0')}:00</text></g>;
        })}
        {showForecast && <path d={forecastPath} className="line-forecast" />}
        {showActual && <path d={actualPath} className="line-actual" />}
        {rows.map((row, index) => {
          const x = xForIndex(index);
          return <g key={row.intervalStart}>
            {showForecast && row.forecastMw !== null && <circle className="point-forecast" cx={x} cy={yFor(row.forecastMw)} r="3.1" tabIndex="0"><title>{timeLabel(row.intervalStart)} forecast: {formatNumber(row.forecastMw)} MW · published {timeLabel(row.forecastPublishTime)}</title></circle>}
            {showActual && row.actualMw !== null && <circle className="point-actual" cx={x} cy={yFor(row.actualMw)} r="2.7" tabIndex="0"><title>{timeLabel(row.intervalStart)} actual: {formatNumber(row.actualMw)} MW</title></circle>}
          </g>;
        })}
      </svg>
      <div className="chart-controls" aria-label="Chart series">
        <button className={'legend-toggle ' + (showForecast ? 'is-on' : '')} type="button" aria-pressed={showForecast} onClick={() => setShowForecast(!showForecast)}><span className="legend-mark forecast-mark" />Forecast</button>
        <button className={'legend-toggle ' + (showActual ? 'is-on' : '')} type="button" aria-pressed={showActual} onClick={() => setShowActual(!showActual)}><span className="legend-mark actual-mark" />Actual</button>
        <span className="chart-footnote">Hourly source pairs · MW · Europe/London</span>
      </div>
      <details className="data-table-details">
        <summary>View hourly values and forecast vintages</summary>
        <div className="table-scroll"><table><caption>Decision {dateLabel(decisionDate, { day: 'numeric', month: 'long', year: 'numeric' })}; delivery {dateLabel(deliveryDate, { day: 'numeric', month: 'long', year: 'numeric' })}</caption>
          <thead><tr><th scope="col">Delivery time</th><th scope="col">Forecast</th><th scope="col">Published</th><th scope="col">Lead</th><th scope="col">Actual</th><th scope="col">Error</th><th scope="col">Actual half-hours</th></tr></thead>
          <tbody>{rows.map((row) => <tr key={row.intervalStart}>
            <th scope="row">{timeLabel(row.intervalStart)}</th>
            <td>{formatNumber(row.forecastMw)} MW</td>
            <td>{timeLabel(row.forecastPublishTime)}</td>
            <td>{row.forecastLeadMinutes === null ? '—' : formatNumber(row.forecastLeadMinutes / 60, 1) + ' h'}</td>
            <td>{formatNumber(row.actualMw)} MW</td>
            <td>{row.errorMw === null ? '—' : signedNumber(row.errorMw) + ' MW'}</td>
            <td>{row.actualHalfHourValuesMw.map((value) => formatNumber(value)).join(' / ')} MW</td>
          </tr>)}</tbody></table></div>
      </details>
    </div>
  );
}

function MetricCard({ label, value, unit, description, tone = 'neutral', chip }) {
  return <article className={'metric-card metric-' + tone}><div className="metric-top"><span className="metric-label">{label}</span>{chip && <span className="metric-chip">{chip}</span>}</div><p className="metric-value">{value}<span>{unit}</span></p><p className="metric-description">{description}</p></article>;
}

function DailyBars({ days, selectedDate, onSelect }) {
  const max = Math.max(...days.map((day) => day.maeMw || 0), 1);
  return <div className="daily-bars" aria-label="Daily mean absolute error, selectable by decision date">
    {days.map((day) => <button key={day.decisionDate} type="button" className={'daily-bar-row ' + (day.decisionDate === selectedDate ? 'selected' : '')} onClick={() => onSelect(day.decisionDate)} aria-pressed={day.decisionDate === selectedDate}>
      <span className="daily-date">{dateLabel(day.decisionDate, { day: '2-digit', month: 'short' })}</span>
      <span className="bar-track"><span className="bar-fill" style={{ width: day.maeMw === null ? '0%' : Math.max(2, (day.maeMw / max) * 100) + '%' }} /></span>
      <span className="daily-value">{formatNumber(day.maeMw)}<small> MW</small></span>
    </button>)}
  </div>;
}

function App() {
  const [theme, setTheme] = useState(() => window.localStorage.getItem('gridline-theme') || 'light');
  const [page, setPage] = useState('overview');
  const [selectedDate, setSelectedDate] = useState('2026-01-15');
  const [auction, setAuction] = useState('gb_30m');
  const [payload, setPayload] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    window.localStorage.setItem('gridline-theme', theme);
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  useEffect(() => {
    const controller = new AbortController();
    setPayload(null);
    setError('');
    fetch('/api/analysis?auction=' + encodeURIComponent(auction), { signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw new Error('Analysis data returned ' + response.status);
        return response.json();
      })
      .then((data) => setPayload(data))
      .catch((reason) => { if (reason.name !== 'AbortError') setError(reason.message); });
    return () => controller.abort();
  }, [auction]);

  const dailyByDate = useMemo(() => new Map(payload?.daily.map((day) => [day.decisionDate, day]) ?? []), [payload]);
  const selectedDay = dailyByDate.get(selectedDate);
  const hourly = useMemo(() => payload?.hourly.filter((row) => row.decisionDate === selectedDate) ?? [], [payload, selectedDate]);

  function downloadCsv() {
    if (!payload) return;
    const blob = new Blob([createAnalysisCsv(payload)], { type: 'text/csv;charset=utf-8' });
    const href = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = href;
    anchor.download = 'gridline-wind-decision-replay-january-2026-' + auction + '.csv';
    anchor.click();
    window.setTimeout(() => URL.revokeObjectURL(href), 1000);
  }

  const nav = <nav className="primary-nav" aria-label="Primary navigation">{NAV_ITEMS.map((item) => <button key={item.id} className={'nav-item ' + (page === item.id ? 'active' : '')} type="button" onClick={() => setPage(item.id)} aria-current={page === item.id ? 'page' : undefined}><Icon name={item.icon} /><span>{item.label}</span></button>)}</nav>;
  const cutoff = payload?.auction.cutoffLocalTime + ' Europe/London';
  const decisionLabel = selectedDay ? dateLabel(selectedDay.decisionDate, { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }) : '';
  const deliveryLabel = selectedDay ? dateLabel(selectedDay.deliveryDate, { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }) : '';

  return <div className="app-shell" data-theme={theme}>
    <aside className="sidebar">
      <a className="brand" href="#main" aria-label="Gridline, skip to analysis"><span className="brand-mark"><span /><span /><span /></span><span className="brand-name">gridline</span></a>
      <div className="workspace-label">WORKSPACE</div>
      {nav}
      <div className="sidebar-bottom">
        <div className="snapshot-card"><span className="snapshot-icon"><Icon name="check" size={15} /></span><span><strong>Historical replay</strong><small>January 2026 · Elexon</small></span></div>
        <p className="sidebar-note">Forecast review<br />National wind generation</p>
      </div>
    </aside>

    <main id="main" className="main-content">
      <header className="topbar"><div className="topbar-context"><span className="context-dot" />UK wholesale · Day ahead</div><div className="topbar-actions"><div className="theme-switch" role="group" aria-label="Color theme"><button type="button" className={theme === 'light' ? 'selected' : ''} aria-pressed={theme === 'light'} onClick={() => setTheme('light')}><Icon name="sun" size={15} /><span>Light</span></button><button type="button" className={theme === 'dark' ? 'selected' : ''} aria-pressed={theme === 'dark'} onClick={() => setTheme('dark')}><Icon name="moon" size={15} /><span>Dark</span></button></div><button className="button button-secondary export-button" onClick={downloadCsv} disabled={!payload} type="button"><Icon name="download" size={16} /><span>Export data</span></button></div></header>

      <div className="content-wrap">
        <div className="page-heading"><div><div className="eyebrow">FORECAST ANALYSIS <span>/</span> JANUARY 2026</div><h1>{page === 'overview' ? 'Wind forecast review' : page === 'accuracy' ? 'Daily accuracy' : 'Method & sources'}</h1><p>{page === 'overview' ? 'See the forecast available at decision time, alongside the generation that followed.' : page === 'accuracy' ? 'Review forecast error across the decision dates and following delivery days.' : 'Trace the replay rules, coverage and source records behind this analysis.'}</p></div><span className="period-pill"><span className="period-icon">D</span> 01–31 Jan decisions · 02 Jan–01 Feb delivery</span></div>

        {!payload && !error && <section className="loading-panel" aria-live="polite"><div className="loading-line" /><div className="loading-line short" /><p>Preparing the verified Elexon replay…</p></section>}
        {error && <section className="error-panel" role="alert"><Icon name="info" /><div><strong>Analysis is unavailable</strong><p>{error}. Check the backend and the included Elexon source records, then reload.</p></div></section>}

        {payload && page === 'overview' && <>
          <section className="metrics-grid" aria-label="Monthly hourly source-series error metrics">
            <MetricCard label="Mean absolute error" value={formatNumber(payload.metrics.maeMw)} unit=" MW" description="Typical error across hourly source pairs" />
            <MetricCard label="Root mean squared error" value={formatNumber(payload.metrics.rmseMw)} unit=" MW" description="Penalizes larger hourly misses" />
            <MetricCard label="Mean bias" value={signedNumber(payload.metrics.meanBiasMw)} unit=" MW" description="Forecast minus actual · monthly mean" chip={payload.metrics.meanBiasMw > 0 ? 'Over-forecast' : payload.metrics.meanBiasMw < 0 ? 'Under-forecast' : null} />
            <MetricCard label="Weighted absolute percentage error" value={formatNumber(payload.metrics.wapePct, 1)} unit="%" description="Σ absolute error ÷ Σ absolute actual" tone="accent" />
          </section>

          <section className="coverage-strip" aria-label="Data coverage and scope">
            <div><strong>{formatNumber(payload.coverage.validMatchedPairs)} / {formatNumber(payload.coverage.expectedIntervals)}</strong><span>matched hourly pairs · {formatNumber(payload.coverage.coveragePct, 1)}%</span></div>
            <div><strong>{formatNumber(payload.coverage.eligibleForecastIntervals)} / {formatNumber(payload.coverage.expectedIntervals)}</strong><span>intervals with an eligible forecast</span></div>
            <div><strong>{formatNumber(payload.coverage.availableActualHalfHours)} / {formatNumber(payload.coverage.expectedActualHalfHours)}</strong><span>available half-hour actual records</span></div>
            <p className="resolution-callout">Comparison grain: {payload.resolution.comparisonIntervalMinutes}-minute source intervals. {payload.resolution.limitation}</p>
            <p>{payload.sources.scopeWarning}</p>
          </section>

          <section className="panel chart-panel" aria-labelledby="hourly-heading">
            <div className="panel-heading"><div><div className="panel-kicker">POINT-IN-TIME REPLAY</div><h2 id="hourly-heading">Forecast vs actual</h2><p>Hourly source comparison using the latest WINDFOR vintage available by the selected EPEX auction-time cutoff.</p></div>
              <div className="analysis-selectors">
                <label className="date-select-label">EPEX auction scenario<select value={auction} onChange={(event) => setAuction(event.target.value)} aria-label="Select EPEX SPOT GB day-ahead auction scenario">{AUCTION_OPTIONS.map((option) => <option key={option.id} value={option.id}>{option.label}</option>)}</select></label>
                <label className="date-select-label">Decision date<select value={selectedDate} onChange={(event) => setSelectedDate(event.target.value)} aria-label="Select decision date">{payload.daily.map((day) => <option key={day.decisionDate} value={day.decisionDate}>{dateLabel(day.decisionDate, { weekday: 'short', day: 'numeric', month: 'short' })} → {dateLabel(day.deliveryDate, { day: 'numeric', month: 'short' })}</option>)}</select></label>
              </div>
            </div>
            {hourly.length > 0 ? <HourlyChart rows={hourly} decisionDate={selectedDate} deliveryDate={selectedDay?.deliveryDate} /> : <p className="inline-empty">No hourly intervals are available for this decision date.</p>}
            <div className="chart-summary">
              <div><span className="summary-label">Decision date</span><strong>{decisionLabel || '—'}</strong></div>
              <div><span className="summary-label">Delivery date</span><strong>{deliveryLabel || '—'}</strong></div>
              <div><span className="summary-label">Auction cutoff</span><strong>{cutoff || '—'}</strong></div>
              <div><span className="summary-label">Unique publication times used</span><strong>{selectedDay ? selectedDay.forecastPublishTimes.length : '—'}</strong></div>
              <div className="coverage-summary"><span className="coverage-indicator"><Icon name="check" size={14} /></span><span><strong>{selectedDay ? selectedDay.validMatchedPairs + '/' + selectedDay.expectedIntervals : '—'}</strong><small>matched hourly pairs</small></span></div>
            </div>
          </section>

          <div className="lower-grid"><section className="panel daily-panel"><div className="lower-heading"><div><div className="panel-kicker">MONTHLY VIEW</div><h2>Daily mean absolute error</h2></div><button className="text-button" type="button" onClick={() => setPage('accuracy')}>View all decision dates <Icon name="arrow" size={15} /></button></div><DailyBars days={payload.daily} selectedDate={selectedDate} onSelect={setSelectedDate} /><p className="bar-scale">Daily MAE, MW · Hourly source pairs · Select a decision date to inspect delivery</p></section><aside className="insight-panel"><div className="insight-icon"><Icon name="info" size={17} /></div><div><h2>Investigate the positive bias</h2><p>Among {formatNumber(payload.metrics.validMatchedPairs)} matched hourly errors, {formatNumber(payload.metrics.positiveErrorCount)} are positive, {formatNumber(payload.metrics.negativeErrorCount)} negative, and {formatNumber(payload.metrics.zeroErrorCount)} zero. Range: {signedNumber(payload.metrics.minErrorMw)} to {signedNumber(payload.metrics.maxErrorMw)} MW. On {formatNumber(payload.daily.filter((day) => day.validMatchedPairs > 0 && day.negativeErrorCount === 0).length)} of {payload.daily.length} decision dates, every matched error is non-negative, so MAE equals mean bias.</p><button className="text-button" type="button" onClick={() => setPage('sources')}>See method & limitations <Icon name="arrow" size={15} /></button></div></aside></div>
        </>}

        {payload && page === 'accuracy' && <section className="panel accuracy-page"><div className="panel-heading"><div><div className="panel-kicker">31 JANUARY DECISION DATES</div><h2>Forecast error by decision date</h2><p>Each row compares the D+1 delivery day; select a row to open its hourly replay.</p></div><span className="table-legend"><span className="legend-mark forecast-mark" />Daily MAE</span></div><div className="accuracy-table-wrap"><table className="accuracy-table"><thead><tr><th scope="col">Decision date</th><th scope="col">Delivery date</th><th scope="col">Daily MAE</th><th scope="col">RMSE</th><th scope="col">Mean bias</th><th scope="col">Matched hourly</th><th scope="col">Signs (+/-/0)</th><th scope="col">Error range (MW)</th><th scope="col">Eligible hourly forecasts</th><th scope="col">Unique publication times</th></tr></thead><tbody>{payload.daily.map((day) => <tr key={day.decisionDate} className={day.decisionDate === selectedDate ? 'selected-row' : ''}><th scope="row"><button className="row-link" type="button" onClick={() => { setSelectedDate(day.decisionDate); setPage('overview'); }}>{dateLabel(day.decisionDate, { weekday: 'short', day: 'numeric', month: 'long' })}</button></th><td>{dateLabel(day.deliveryDate, { day: 'numeric', month: 'short' })}</td><td><span className="table-metric">{formatNumber(day.maeMw)} MW</span>{day.maeMw !== null && <span className="mini-track"><span style={{ width: Math.max(2, (day.maeMw / Math.max(...payload.daily.map((entry) => entry.maeMw || 0), 1)) * 100) + '%' }} /></span>}</td><td>{formatNumber(day.rmseMw)} MW</td><td className={day.meanBiasMw >= 0 ? 'positive-bias' : 'negative-bias'}>{signedNumber(day.meanBiasMw)} MW</td><td><span className="coverage-tag">{day.validMatchedPairs}/{day.expectedIntervals} {formatNumber(day.coveragePct, 0)}%</span></td><td>{day.positiveErrorCount}/{day.negativeErrorCount}/{day.zeroErrorCount}</td><td>{signedNumber(day.minErrorMw)} to {signedNumber(day.maxErrorMw)}</td><td>{day.eligibleForecastIntervals}/{day.expectedIntervals}</td><td>{day.forecastPublishTimes.length} {day.forecastPublishTimes.length === 1 ? 'publication time' : 'publication times'}</td></tr>)}</tbody></table></div></section>}

        {payload && page === 'sources' && <div className="source-layout"><section className="panel method-panel"><div className="panel-kicker">REPLAY METHOD</div><h2>What was available at decision time?</h2><p className="section-intro">January decision date D maps to next-day delivery D+1. The selectable cutoffs use EPEX SPOT GB day-ahead auction times in Europe/London as prototype replay boundaries. They are not verified decision deadlines for every buyer or venue.</p><ol className="method-steps">
          <li><span>01</span><div><strong>Set the decision boundary</strong><p>EPEX SPOT documents the GB 60-minute and 30-minute local day-ahead auction times at 09:20 and 15:30 GMT. This replay uses those published times as prototype cutoffs. Nord Pool N2EX is a separate hourly auction with a documented 09:50 GMT gate closure and is not modeled here. All dates use Europe/London; January is GMT.</p></div></li>
          <li><span>02</span><div><strong>Select a forecast vintage</strong><p>For each hourly delivery interval, select the latest WINDFOR publishTime at or before the selected EPEX auction-time cutoff. Exact-cutoff records are eligible; later vintages cannot fill gaps. This replay uses only archived Elexon records, never current forecasts.</p></div></li>
          <li><span>03</span><div><strong>Align the source intervals</strong><p>Elexon WINDFOR is an hourly forecast in average MW. FUELHH actuals are half-hour average MW, so averaging the two equal-duration actuals yields the hourly average. Both actual half-hours must exist. The source data cannot measure 30-minute forecast accuracy; the 30-minute auction scenario still reports hourly source comparisons.</p></div></li>
          <li><span>04</span><div><strong>Measure and expose coverage</strong><p>MAE, RMSE, mean bias, WAPE, error signs, and error range are recomputed from unrounded matched hourly errors. Coverage uses 744 expected hourly comparisons for either selected cutoff. This resolution is aligned with WINDFOR and is not a half-hourly forecast evaluation.</p></div></li>
        </ol>
          <div className="limitation-note"><strong>Source scope limitation</strong><p>Elexon describes WINDFOR forecasts for wind farms visible to ESO with operational metering and FUELHH as generation by fuel type. The exact asset populations are not shown to be identical. These are errors between the specified source series, not a definitive national wind forecast error or procurement recommendation.</p></div>
        </section>
          <aside className="source-column"><section className="panel source-panel"><div className="panel-kicker">SOURCE RECORDS</div><h2>Official Elexon data</h2><a className="source-link" href={payload.sources.forecastUrl} target="_blank" rel="noreferrer"><span><strong>WINDFOR</strong><small>Hourly wind generation forecasts · MW</small></span><Icon name="arrow" size={16} /></a><a className="source-link" href={payload.sources.actualUrl} target="_blank" rel="noreferrer"><span><strong>FUELHH · WIND</strong><small>Half-hour generation actuals · MW</small></span><Icon name="arrow" size={16} /></a><div className="source-meta"><span>Snapshot updated</span><strong>{payload.sources.retrievedAtUtc ? new Intl.DateTimeFormat('en-GB', { dateStyle: 'medium', timeStyle: 'short', timeZone: 'UTC' }).format(new Date(payload.sources.retrievedAtUtc)) + ' UTC' : 'Not recorded'}</strong></div><div className="source-meta"><span>Matched hourly pairs</span><strong>{formatNumber(payload.coverage.validMatchedPairs)} / {formatNumber(payload.coverage.expectedIntervals)}</strong></div><div className="source-meta"><span>Eligible forecasts</span><strong>{formatNumber(payload.coverage.eligibleForecastIntervals)} / {formatNumber(payload.coverage.expectedIntervals)}</strong></div><div className="source-meta"><span>Available actual half-hours</span><strong>{formatNumber(payload.coverage.availableActualHalfHours)} / {formatNumber(payload.coverage.expectedActualHalfHours)}</strong></div><div className="source-meta"><span>Later forecast records excluded for this scenario</span><strong>{formatNumber(payload.coverage.postCutoffForecastRecordsExcluded)}</strong></div><p className="source-meta-note">Counts distinct WINDFOR (startTime, publishTime) vintages after identical duplicates are collapsed, limited to the {formatNumber(payload.coverage.expectedIntervals)} expected hourly D+1 delivery starts, where publishTime is after that decision date's cutoff. Snapshot publication-time query windows: {payload.sources.forecastPublicationQueryWindow?.startUtc} to {payload.sources.forecastPublicationQueryWindow?.endUtc} UTC across {payload.sources.forecastPublicationQueryWindow?.requestCount} manifest requests; this is not all Elexon forecast history.</p></section>
            <section className="panel definitions-panel"><div className="panel-kicker">METRIC DEFINITIONS</div><dl><div><dt>MAE</dt><dd>Mean absolute hourly error over matched pairs, in MW.</dd></div><div><dt>RMSE</dt><dd>Square root of mean squared hourly error, in MW.</dd></div><div><dt>Bias</dt><dd>Mean signed forecast-minus-actual error, in MW.</dd></div><div><dt>WAPE</dt><dd>Sum of absolute errors divided by sum of absolute actual MW, as a percentage.</dd></div></dl></section>
            <section className="panel definitions-panel"><div className="panel-kicker">REFERENCE</div><a className="source-link" href={payload.auction.referenceUrl} target="_blank" rel="noreferrer"><span><strong>EPEX SPOT</strong><small>GB day-ahead auction times and products</small></span><Icon name="arrow" size={16} /></a><a className="source-link" href={payload.auction.n2exReferenceUrl} target="_blank" rel="noreferrer"><span><strong>Nord Pool N2EX</strong><small>Separate UK hourly day-ahead auction</small></span><Icon name="arrow" size={16} /></a><p className="reference-note">{payload.auction.n2exNote} WINDFOR forecast and FUELHH actual records are included with the project; query windows are in the manifest. <a href="https://bmrs.elexon.co.uk/wind-generation" target="_blank" rel="noreferrer">Elexon hourly wind forecast definition</a> and <a href="https://www.elexon.co.uk/bsc/glossary/half-hourly-generation-by-fuel-type/" target="_blank" rel="noreferrer">FUELHH half-hour average-MW definition</a>.</p></section>
          </aside>
        </div>}

        <footer className="page-footer"><span>Gridline <span className="footer-dot">·</span> January 2026 decision replay</span><span>Source: Elexon BMRS · Wind only · {payload ? payload.auction.label : 'Loading auction scenario'}</span></footer>
      </div>
    </main>
    <div className="mobile-nav">{nav}</div>
  </div>;
}

export default App;
