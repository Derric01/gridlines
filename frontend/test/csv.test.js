import assert from 'node:assert/strict';
import test from 'node:test';
import { createAnalysisCsv, createCsv } from '../src/csv.js';

test('exports aligned decision and delivery interval fields without recalculation', () => {
  const csv = createCsv([{
    auctionScenario: 'EPEX SPOT GB 30-minute day-ahead auction',
    auctionCutoffLocalTime: '15:30',
    comparisonIntervalMinutes: 60,
    decisionDate: '2026-01-31',
    decisionCutoffLocal: '2026-01-31T15:30:00+00:00',
    deliveryDate: '2026-02-01',
    intervalStart: '2026-02-01T23:00:00Z',
    intervalEnd: '2026-02-02T00:00:00Z',
    forecastPublishTime: '2026-01-31T15:30:00Z',
    forecastLeadMinutes: 1890,
    forecastMw: 5099,
    actualMw: 5216,
    errorMw: -117,
    validMatched: true,
  }]);

  assert.equal(csv.split('\r\n').length, 2);
  assert.match(csv, /auctionScenario,auctionCutoffLocalTime,comparisonIntervalMinutes,decisionDate/);
  assert.match(csv, /EPEX SPOT GB 30-minute day-ahead auction,15:30,60,2026-01-31/);
  assert.match(csv, /decisionDate,decisionCutoffLocal,deliveryDate/);
  assert.match(csv, /2026-01-31,2026-01-31T15:30:00\+00:00,2026-02-01/);
  assert.match(csv, /5099,5216,-117,true$/);
});

test('retains incomplete hourly rows and leaves missing values blank', () => {
  const csv = createCsv([{
    decisionDate: '2026-01-01',
    deliveryDate: '2026-01-02',
    intervalStart: '2026-01-02T00:00:00Z',
    intervalEnd: '2026-01-02T01:00:00Z',
    forecastMw: null,
    actualMw: null,
    errorMw: null,
    validMatched: false,
  }]);

  const [header, row] = csv.split('\r\n');
  assert.equal(header.split(',').length, 14);
  assert.equal(row.split(',').length, 14);
  assert.match(row, /2026-01-02T00:00:00Z,2026-01-02T01:00:00Z,,,,,,false$/);
});

test('escapes commas, quotes, and line breaks in CSV values', () => {
  const csv = createCsv([{ decisionDate: '2026-01-01, "test"\nnext' }]);
  assert.ok(csv.includes(',,,"2026-01-01, ""test""\nnext",'));
});

test('exports the selected analysis payload and its scenario-specific vintages', () => {
  const commonRow = {
    decisionDate: '2026-01-01',
    decisionCutoffLocal: '2026-01-01T09:20:00+00:00',
    deliveryDate: '2026-01-02',
    intervalStart: '2026-01-02T00:00:00Z',
    intervalEnd: '2026-01-02T01:00:00Z',
    forecastPublishTime: '2026-01-01T07:30:00Z',
    forecastMw: 18781,
    actualMw: 18000,
    errorMw: 781,
    validMatched: true,
  };
  const hourlyCsv = createAnalysisCsv({
    auction: { marketLabel: 'EPEX SPOT GB 60-minute day-ahead auction', cutoffLocalTime: '09:20' },
    resolution: { comparisonIntervalMinutes: 60 },
    hourly: [commonRow],
  });
  const halfHourCsv = createAnalysisCsv({
    auction: { marketLabel: 'EPEX SPOT GB 30-minute day-ahead auction', cutoffLocalTime: '15:30' },
    resolution: { comparisonIntervalMinutes: 60 },
    hourly: [{ ...commonRow, decisionCutoffLocal: '2026-01-01T15:30:00+00:00', forecastPublishTime: '2026-01-01T15:30:00Z', forecastMw: 18804, errorMw: 804 }],
  });

  assert.notEqual(hourlyCsv, halfHourCsv);
  assert.match(hourlyCsv, /EPEX SPOT GB 60-minute day-ahead auction,09:20,60/);
  assert.match(hourlyCsv, /2026-01-01T07:30:00Z,,18781,18000,781,true$/);
  assert.match(halfHourCsv, /EPEX SPOT GB 30-minute day-ahead auction,15:30,60/);
  assert.match(halfHourCsv, /2026-01-01T15:30:00Z,,18804,18000,804,true$/);
});
