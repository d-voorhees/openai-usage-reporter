import os
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
EMAIL_FROM = os.getenv("EMAIL_FROM")
EMAIL_TO = os.getenv("EMAIL_TO")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))

def get_usage(start_date, end_date):
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
    params = {"start_date": start_date, "end_date": end_date}

    response = requests.get(
        "https://api.openai.com/v1/usage",
        headers=headers,
        params=params
    )
    response.raise_for_status()
    return response.json()

def get_subscription():
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
    response = requests.get(
        "https://api.openai.com/v1/dashboard/billing/subscription",
        headers=headers
    )
    response.raise_for_status()
    return response.json()

def format_report(yesterday_data, month_data, subscription):
    yesterday_total = sum(item.get("total_usage", 0) for item in yesterday_data.get("data", [])) / 100
    month_total = sum(item.get("total_usage", 0) for item in month_data.get("data", [])) / 100

    billing_cycle = subscription.get("billing_cycle", "unknown")
    soft_limit = subscription.get("soft_limit_usd", "N/A")

    report = f"""
OpenAI API Usage Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}

Yesterday's Usage
- Total: ${yesterday_total:.2f}

This Month's Usage
- Total: ${month_total:.2f}
- Billing Cycle: {billing_cycle}
- Soft Limit: ${soft_limit}
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
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    month_start = today.replace(day=1)

    yesterday_data = get_usage(yesterday.isoformat(), yesterday.isoformat())
    month_data = get_usage(month_start.isoformat(), today.isoformat())
    subscription = get_subscription()

    report = format_report(yesterday_data, month_data, subscription)
    send_email(f"OpenAI Usage Report - {yesterday}", report)
    print(f"Report sent for {yesterday}")

if __name__ == "__main__":
    main()
