import os
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
EMAIL_FROM = os.getenv("EMAIL_FROM")
EMAIL_TO = os.getenv("EMAIL_TO")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))

REPORT_TZ = timezone(timedelta(hours=-6))

def fetch_cost_results(start_time, end_time, group_by=None):
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
    params = {
        "start_time": start_time,
        "end_time": end_time,
        "bucket_width": "1d",
        "limit": 31,
    }
    if group_by:
        params["group_by"] = group_by

    results = []
    page = None
    while True:
        if page:
            params["page"] = page

        response = requests.get(
            "https://api.openai.com/v1/organization/costs",
            headers=headers,
            params=params
        )
        response.raise_for_status()
        payload = response.json()

        for bucket in payload.get("data", []):
            results.extend(bucket.get("results", []))

        if payload.get("has_more"):
            page = payload.get("next_page")
        else:
            break

    return results

def get_cost(start_time, end_time):
    results = fetch_cost_results(start_time, end_time)
    return sum(float(r.get("amount", {}).get("value", 0) or 0) for r in results)

def get_cost_by_key(start_time, end_time):
    results = fetch_cost_results(start_time, end_time, group_by=["api_key_id"])

    breakdown = {}
    for result in results:
        key_id = result.get("api_key_id") or "unassigned"
        amount = float(result.get("amount", {}).get("value", 0) or 0)
        breakdown[key_id] = breakdown.get(key_id, 0.0) + amount

    return {key_id: amount for key_id, amount in breakdown.items() if round(amount, 2) != 0}

def get_api_key_names():
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
    names = {}

    try:
        projects = []
        after = None
        while True:
            params = {"limit": 100}
            if after:
                params["after"] = after
            response = requests.get(
                "https://api.openai.com/v1/organization/projects",
                headers=headers,
                params=params
            )
            response.raise_for_status()
            payload = response.json()
            projects.extend(payload.get("data", []))
            if payload.get("has_more"):
                after = payload.get("last_id")
            else:
                break
    except requests.RequestException:
        return names

    for project in projects:
        project_id = project.get("id")
        if not project_id:
            continue
        try:
            after = None
            while True:
                params = {"limit": 100}
                if after:
                    params["after"] = after
                response = requests.get(
                    f"https://api.openai.com/v1/organization/projects/{project_id}/api_keys",
                    headers=headers,
                    params=params
                )
                response.raise_for_status()
                payload = response.json()
                for key in payload.get("data", []):
                    if key.get("id"):
                        names[key["id"]] = key.get("name") or key["id"]
                if payload.get("has_more"):
                    after = payload.get("last_id")
                else:
                    break
        except requests.RequestException:
            continue

    return names

def format_key_breakdown(breakdown, key_names):
    if not breakdown:
        return ["No per-key usage recorded"]

    lines = []
    for key_id, amount in sorted(breakdown.items(), key=lambda item: -item[1]):
        if key_id == "unassigned":
            label = "Other (no key attribution)"
        else:
            name = key_names.get(key_id)
            label = f"{name} (…{key_id[-6:]})" if name else key_id
        lines.append(f"{label}: ${amount:.2f}")

    return lines

def format_period(start, end):
    fmt = "%b %d, %Y %I:%M %p"
    return f"{start.strftime(fmt)} GMT-6 to {end.strftime(fmt)} GMT-6"

def format_report_text(yesterday_total, yesterday_period, yesterday_by_key, month_total, month_period, month_by_key, key_names, generated):
    yesterday_lines = "\n".join(f"  - {line}" for line in format_key_breakdown(yesterday_by_key, key_names))
    month_lines = "\n".join(f"  - {line}" for line in format_key_breakdown(month_by_key, key_names))

    return f"""
OpenAI API Usage Report
Generated: {generated.strftime('%Y-%m-%d %H:%M')} GMT-6

Yesterday's Usage
{yesterday_period}
- Total: ${yesterday_total:.2f}
- By API Key:
{yesterday_lines}

This Month's Usage
{month_period}
- Total: ${month_total:.2f}
- By API Key:
{month_lines}
    """.strip()

def format_report_html(yesterday_total, yesterday_period, yesterday_by_key, month_total, month_period, month_by_key, key_names, generated):
    yesterday_items = "".join(f"<li>{line}</li>" for line in format_key_breakdown(yesterday_by_key, key_names))
    month_items = "".join(f"<li>{line}</li>" for line in format_key_breakdown(month_by_key, key_names))

    return f"""\
<html>
  <body>
    <p><b>OpenAI API Usage Report</b><br>
    Generated: {generated.strftime('%Y-%m-%d %H:%M')} GMT-6</p>
    <p><b>Yesterday's Usage</b><br>
    {yesterday_period}<br>
    Total: ${yesterday_total:.2f}<br>
    By API Key:</p>
    <ul>{yesterday_items}</ul>
    <p><b>This Month's Usage</b><br>
    {month_period}<br>
    Total: ${month_total:.2f}<br>
    By API Key:</p>
    <ul>{month_items}</ul>
  </body>
</html>
"""

def send_email(subject, text_body, html_body):
    msg = MIMEMultipart('alternative')
    msg['From'] = EMAIL_FROM
    msg['To'] = EMAIL_TO
    msg['Subject'] = subject
    msg.attach(MIMEText(text_body, 'plain'))
    msg.attach(MIMEText(html_body, 'html'))

    if SMTP_PORT == 465:
        server = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT)
    else:
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        server.starttls()

    server.login(EMAIL_FROM, EMAIL_PASSWORD)
    server.send_message(msg)
    server.quit()

def main():
    now = datetime.now(timezone.utc).astimezone(REPORT_TZ)
    today = now.date()
    yesterday = today - timedelta(days=1)
    month_start = today.replace(day=1)

    def midnight(d):
        return datetime.combine(d, datetime.min.time(), tzinfo=REPORT_TZ)

    yesterday_start = midnight(yesterday)
    yesterday_end = midnight(today)
    month_start_dt = midnight(month_start)

    yesterday_start_ts = int(yesterday_start.timestamp())
    yesterday_end_ts = int(yesterday_end.timestamp())
    month_start_ts = int(month_start_dt.timestamp())
    now_ts = int(now.timestamp())

    yesterday_total = get_cost(yesterday_start_ts, yesterday_end_ts)
    month_total = get_cost(month_start_ts, now_ts)

    yesterday_by_key = get_cost_by_key(yesterday_start_ts, yesterday_end_ts)
    month_by_key = get_cost_by_key(month_start_ts, now_ts)
    key_names = get_api_key_names()

    yesterday_period = format_period(yesterday_start, yesterday_end)
    month_period = format_period(month_start_dt, now)

    text_body = format_report_text(yesterday_total, yesterday_period, yesterday_by_key, month_total, month_period, month_by_key, key_names, now)
    html_body = format_report_html(yesterday_total, yesterday_period, yesterday_by_key, month_total, month_period, month_by_key, key_names, now)

    send_email("OpenAI API Usage Report", text_body, html_body)
    print(f"Report sent for {yesterday}")

if __name__ == "__main__":
    main()
