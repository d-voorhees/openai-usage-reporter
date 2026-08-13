# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [1.1.0] - 2026-08-13

### Added
- Per-API-key cost breakdown in both the yesterday and month-to-date sections of the report, using the Costs API's `group_by=api_key_id` support.
- API key name resolution: the script looks up key names across all projects so the report shows human-readable labels (e.g. `Production Server (…a1b2c3)`) instead of bare key IDs. If name lookup fails (insufficient scope, network error, etc.), it falls back to showing the raw key ID rather than failing the whole report.

### Changed
- `get_cost()` now shares its pagination logic with the new `get_cost_by_key()` through a common `fetch_cost_results()` helper, instead of duplicating the request loop.

## [1.0.0] - 2026-08-11

### Added
- Initial release: daily and month-to-date OpenAI usage cost totals via the `/v1/organization/costs` endpoint.
- Plain-text and HTML email report with explicit period start/end times.
- GitHub Actions workflow for a free daily scheduled run.
