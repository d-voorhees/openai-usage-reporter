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
                total += result.get("amount", {}).get("value", 0)

        if payload.get("has_more"):
            page = payload.get("next_page")
        else:
            break

    return total

def format_report(yesterday_total, month_total):
    report = f"""
OpenAI API Usage Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}

Yesterday's Usage
- Total: ${yesterday_total:.2f}

This Month's Usage
- Total: ${month_total:.2f}
    """.strip()

    return report

def send_email(subject, body):
    msg = MIMEMultipart()
    msg['From'] = EMAIL_FROM
    msg['To'] = EMAIL_TO
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    if SMTP_PORT == 465:
        server = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT)
    else:
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        server.starttls()

    server.login(EMAIL_FROM, EMAIL_PASSWORD)
    server.send_message(msg)
    server.quit()

def main():
    today = datetime.now(timezone.utc).date()
    yesterday = today - timedelta(days=1)
    month_start = today.replace(day=1)

    def start_of_day(d):
        return int(datetime.combine(d, datetime.min.time(), tzinfo=timezone.utc).timestamp())

    yesterday_total = get_cost(start_of_day(yesterday), start_of_day(today))
    month_total = get_cost(start_of_day(month_start), start_of_day(today + timedelta(days=1)))

    report = format_report(yesterday_total, month_total)
    send_email(f"OpenAI Usage Report - {yesterday}", report)
    print(f"Report sent for {yesterday}")

if __name__ == "__main__":
    main()
