# OpenAI Usage Reporter

This project runs a daily OpenAI API usage check and sends an email with the numbers. It uses GitHub Actions as a free scheduler and avoids any extra infrastructure.

Companion post: [The Daily OpenAI Usage Email Report](https://dvoorhees.com/2026/08/05/how-i-built-a-free-daily-openai-usage-email-report/)

## What it does

- Queries the OpenAI billing API for today's usage.
- Formats a short plain-text report.
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

1. Fork or clone this repository — `report.py`, `requirements.txt`, and the workflow file are already included.
2. Add the six repository secrets (see [Environment variables](#environment-variables)):
   - On GitHub, go to **Settings → Secrets and variables → Actions → New repository secret**.
   - Add `OPENAI_API_KEY`, `EMAIL_FROM`, `EMAIL_TO`, `EMAIL_PASSWORD`, `SMTP_HOST`, and `SMTP_PORT`, one at a time.
3. Test it: go to the **Actions** tab, select **Daily OpenAI Usage Report**, click **Run workflow**, and confirm the email arrives.
4. If it works, you're done — the workflow runs automatically on the cron schedule below.

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

- `OPENAI_API_KEY`: Your OpenAI API key with billing access. This script calls the legacy `/v1/usage` and `/v1/dashboard/billing/subscription` endpoints — if your key returns a 401, you may need an admin-scoped key or to switch to OpenAI's newer Usage/Costs API endpoints.
- `EMAIL_FROM`: The sender address for your SMTP account.
- `EMAIL_TO`: The destination email address.
- `EMAIL_PASSWORD`: The password (or app password, if your provider requires one) for the sender account.
- `SMTP_HOST`: Your SMTP provider's server, for example `smtp.yourprovider.com`.
- `SMTP_PORT`: The SMTP port. Use `587` (STARTTLS) unless your provider requires implicit SSL on `465`.

This project connects to whatever SMTP server you point it at — it isn't tied to Gmail. If you want to use Gmail anyway, see [Using Gmail](#using-gmail) below.

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

If the test run in the Actions tab fails, check the run's log for these two common cases:

- **401 from OpenAI**: your API key doesn't have access to the legacy `/v1/usage` and `/v1/dashboard/billing/subscription` endpoints. Try an admin-scoped key from your org's settings, or migrate `report.py` to OpenAI's newer Usage/Costs API.
- **SMTP authentication error**: double check `EMAIL_PASSWORD` — most providers (Gmail included) require an app password rather than your normal account password. Also confirm `SMTP_PORT` matches your provider (`465` for implicit SSL, `587` for STARTTLS) — a mismatched port produces a connection or auth error rather than a clear "wrong port" message.

## Tests

This project does not include an automated test suite yet. For a small personal tool, the most useful next step is usually to add mocked tests around the API calls and email formatting before expanding the feature set.

## Tradeoffs

This stays intentionally small. A serverless workflow is easier to maintain than a hosted app for a one-job utility, and a plain email report is cheaper and less distracting than a dashboard.

The current implementation assumes one sender account and one recipient. That keeps the setup simple and avoids turning a utility script into a mini platform.

## License

MIT — see [LICENSE](LICENSE).