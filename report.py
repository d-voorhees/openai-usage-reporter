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

def get_cost(start_time, end_time):
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
    params = {
        "start_time": start_time,
        "end_time": end_time,
        "bucket_width": "1d",
        "limit": 31,
    }

    total = 0.0
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
            for result in bucket.get("results", []):
                total += float(result.get("amount", {}).get("value", 0) or 0)

        if payload.get("has_more"):
            page = payload.get("next_page")
        else:
            break

    return total

def format_period(start, end):
    fmt = "%b %d, %Y %I:%M %p"
    return f"{start.strftime(fmt)} GMT-6 to {end.strftime(fmt)} GMT-6"

def format_report_text(yesterday_total, yesterday_period, month_total, month_period, generated):
    return f"""
OpenAI API Usage Report
Generated: {generated.strftime('%Y-%m-%d %H:%M')} GMT-6

Yesterday's Usage
{yesterday_period}
- Total: ${yesterday_total:.2f}

This Month's Usage
{month_period}
- Total: ${month_total:.2f}
    """.strip()

def format_report_html(yesterday_total, yesterday_period, month_total, month_period, generated):
    return f"""\
<html>
  <body>
    <p><b>OpenAI API Usage Report</b><br>
    Generated: {generated.strftime('%Y-%m-%d %H:%M')} GMT-6</p>
    <p><b>Yesterday's Usage</b><br>
    {yesterday_period}<br>
    Total: ${yesterday_total:.2f}</p>
    <p><b>This Month's Usage</b><br>
    {month_period}<br>
    Total: ${month_total:.2f}</p>
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

    yesterday_total = get_cost(int(yesterday_start.timestamp()), int(yesterday_end.timestamp()))
    month_total = get_cost(int(month_start_dt.timestamp()), int(now.timestamp()))

    yesterday_period = format_period(yesterday_start, yesterday_end)
    month_period = format_period(month_start_dt, now)

    text_body = format_report_text(yesterday_total, yesterday_period, month_total, month_period, now)
    html_body = format_report_html(yesterday_total, yesterday_period, month_total, month_period, now)

    send_email("OpenAI API Usage Report", text_body, html_body)
    print(f"Report sent for {yesterday}")

if __name__ == "__main__":
    main()
