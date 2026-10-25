export const CSV_COLUMNS = [
  'auctionScenario',
  'auctionCutoffLocalTime',
  'comparisonIntervalMinutes',
  'decisionDate',
  'decisionCutoffLocal',
  'deliveryDate',
  'intervalStart',
  'intervalEnd',
  'forecastPublishTime',
  'forecastLeadMinutes',
  'forecastMw',
  'actualMw',
  'errorMw',
  'validMatched',
];

function csvCell(value) {
  if (value === null || value === undefined) return '';
  const text = String(value);
  return /[",\r\n]/.test(text) ? '"' + text.replaceAll('"', '""') + '"' : text;
}

export function createCsv(rows) {
  const lines = [
    CSV_COLUMNS.join(','),
    ...rows.map((row) => CSV_COLUMNS.map((column) => csvCell(row[column])).join(',')),
  ];
  return lines.join('\r\n');
}

export function createAnalysisCsv(payload) {
  const rows = payload.hourly.map((row) => ({
    ...row,
    auctionScenario: payload.auction.marketLabel,
    auctionCutoffLocalTime: payload.auction.cutoffLocalTime,
    comparisonIntervalMinutes: payload.resolution.comparisonIntervalMinutes,
  }));
  return createCsv(rows);
}
