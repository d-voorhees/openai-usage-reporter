# OpenAI Usage Reporter

This project runs a daily OpenAI API usage check and sends an email with the numbers. It uses GitHub Actions as a free scheduler and avoids any extra infrastructure.

Companion post: [The Daily OpenAI Usage Email Report](https://dvoorhees.com/2026/08/05/how-i-built-a-free-daily-openai-usage-email-report/?utm_source=github&utm_medium=referral&utm_campaign=openai-usage-reporter)

## What it does

- Queries OpenAI's Costs API for yesterday's usage and month-to-date usage.
- Formats a short report (plain text + HTML, with bold section headers) stating the exact date/time period each total covers.
- Sends the report to a configured email address.
- Runs on a cron schedule inside GitHub Actions.

## How it is structured

```text
.
├── report.py
├── requirements.txt
└── .github/workflows/daily-report.yml
```

`report.py` handles the API calls, report formatting, and email delivery. The workflow file defines the daily schedule and environment variables.

## Setup

> [!IMPORTANT]
> `OPENAI_API_KEY` must be an **admin API key** (`sk-admin-...`), not a regular project key (`sk-proj-...`). Regular project keys cannot read the Costs API and will fail with a 400 or 401 error. Generate one at **[platform.openai.com/settings/organization/admin-keys](https://platform.openai.com/settings/organization/admin-keys)** — you must be the org owner (or have an admin role) to see that page.

1. Fork or clone this repository — `report.py`, `requirements.txt`, and the workflow file are already included.
2. Generate an admin API key at [platform.openai.com/settings/organization/admin-keys](https://platform.openai.com/settings/organization/admin-keys) (see the note above — this is not the same as a normal API key).
3. Add the six repository secrets (see [Environment variables](#environment-variables)):
   - On GitHub, go to **Settings → Secrets and variables → Actions → New repository secret**.
   - Add `OPENAI_API_KEY` (the admin key from step 2), `EMAIL_FROM`, `EMAIL_TO`, `EMAIL_PASSWORD`, `SMTP_HOST`, and `SMTP_PORT`, one at a time.
4. Test it: go to the **Actions** tab, select **Daily OpenAI Usage Report**, click **Run workflow**, and confirm the email arrives.
5. If it works, you're done — the workflow runs automatically on the cron schedule below.

To run it locally instead of (or before) pushing to GitHub:

```bash
git clone https://github.com/YOUR-USERNAME/openai-usage-reporter.git
cd openai-usage-reporter
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Environment variables

Set these as GitHub Actions secrets and, if you test locally, as environment variables.

- `OPENAI_API_KEY`: An **admin API key** (`sk-admin-...`) — **not** a regular project key (`sk-proj-...`). This script calls the `/v1/organization/costs` endpoint, which requires `api.usage.read` scope that only admin keys carry. Generate one at [platform.openai.com/settings/organization/admin-keys](https://platform.openai.com/settings/organization/admin-keys) (org owner/admin role required to see that page).
- `EMAIL_FROM`: The sender address for your SMTP account.
- `EMAIL_TO`: The destination email address.
- `EMAIL_PASSWORD`: The password (or app password, if your provider requires one) for the sender account.
- `SMTP_HOST`: Your SMTP provider's server, for example `smtp.yourprovider.com`.
- `SMTP_PORT`: The SMTP port. Use `587` (STARTTLS) unless your provider requires implicit SSL on `465`.

This project connects to whatever SMTP server you point it at — it isn't tied to Gmail. If you want to use Gmail anyway, see [Using Gmail](#using-gmail) below.

## Report format

- **Subject**: always `OpenAI API Usage Report`.
- **Body**: sent as both plain text and HTML (most email clients show the HTML version, with **bold** section headers — `OpenAI API Usage Report`, `Yesterday's Usage`, `This Month's Usage`). Clients that can't render HTML fall back to the plain-text version, which has the same content unbolded.
- **Periods**: each section states the exact start and end of the period it covers, e.g. `Aug 10, 2026 12:00 AM GMT-6 to Aug 11, 2026 12:00 AM GMT-6`, rather than just saying "yesterday." Times are always shown on a fixed GMT-6 offset, regardless of where or when the GitHub Actions runner executes — this is independent of the DST-adjusted Mountain Time cron schedule described in [Scheduled run](#scheduled-run) below.
- **Yesterday's Usage**: the full prior calendar day, midnight to midnight, GMT-6.
- **This Month's Usage**: month-to-date, from midnight GMT-6 on the 1st of the current month through the moment the report ran.

## Run locally

```bash
export OPENAI_API_KEY="..."
export EMAIL_FROM="..."
export EMAIL_TO="..."
export EMAIL_PASSWORD="..."
export SMTP_HOST="..."
export SMTP_PORT="587"
python report.py
```

The script reads the current date, queries usage for the current day, and emails the result.

## Using Gmail

This project defaults to a generic SMTP setup so it isn't locked to one provider, but Gmail works fine if you'd rather use it:

1. Enable 2-Step Verification on the Google account.
2. Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords) and create an app password for "Mail".
3. Set `EMAIL_FROM` to the Gmail address, `EMAIL_PASSWORD` to the generated app password (not the regular account password), `SMTP_HOST` to `smtp.gmail.com`, and `SMTP_PORT` to `465`.

## Scheduled run

The workflow runs at 10 PM Mountain Time by using a GitHub Actions cron schedule in UTC.

```yaml
on:
  schedule:
    - cron: '0 4 * * *'
```

GitHub Actions cron doesn't adjust for daylight saving automatically, so this drifts an hour twice a year:

- `0 4 * * *` = 10 PM MDT (roughly early March–early November)
- `0 5 * * *` = 10 PM MST (roughly early November–early March)

Flip the value in `.github/workflows/daily-report.yml` when the clocks change, or adjust it for your own timezone if you're not on Mountain Time.

## Troubleshooting

If the test run in the Actions tab fails, check the run's log for these common cases:

- **400 or 401 from OpenAI**: `OPENAI_API_KEY` isn't an admin-scoped key. Regular project keys (`sk-proj-...`) can't read `/v1/organization/costs` — generate an admin key from your org's settings and use that instead.
- **SMTP authentication error**: double check `EMAIL_PASSWORD` — most providers (Gmail included) require an app password rather than your normal account password. Also confirm `SMTP_PORT` matches your provider (`465` for implicit SSL, `587` for STARTTLS) — a mismatched port produces a connection or auth error rather than a clear "wrong port" message.

## Tests

This project does not include an automated test suite yet. For a small personal tool, the most useful next step is usually to add mocked tests around the API calls and email formatting before expanding the feature set.

## Tradeoffs

This stays intentionally small. A serverless workflow is easier to maintain than a hosted app for a one-job utility, and a plain email report is cheaper and less distracting than a dashboard.

The current implementation assumes one sender account and one recipient. That keeps the setup simple and avoids turning a utility script into a mini platform.

## License

MIT — see [LICENSE](LICENSE).