from confluent_kafka import Consumer
import time, json, smtplib
from email.mime.text import MIMEText
import os
from dotenv import load_dotenv

load_dotenv() 

sender_email = os.getenv("EMAIL_ADDRESS")
password = os.getenv("EMAIL_PASSWORD")
SMTP_HOST = os.getenv("EMAIL_HOST")
SMTP_PORT = int(os.getenv("EMAIL_PORT", 587))


config = {
    'bootstrap.servers': 'kafka:9092',
    'group.id': 'retro-games-email-service',
    'auto.offset.reset': 'earliest'
}


def send_email(to_email, subject, body):
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = to_email

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(sender_email, password)
            server.sendmail(sender_email, to_email, msg.as_string())
            print(f"Email sent to {to_email}")
    except Exception as e:
        print(f"Failed to send email to {to_email}: {e}")

# wait for Kafka
while True:
    try:
        consumer = Consumer(config)
        consumer.subscribe(['notifications'])
        print("Kafka consumer started!")
        break
    except Exception as e:
        print(f"Kafka not ready: {e}, retrying in 5s...")
        time.sleep(5)

# Consumer loop
try:
    while True:
        msg = consumer.poll(1.0)

        if msg is None:
            continue

        if msg.error():
            print(f"Consumer error: {msg.error()}")
            continue

        event = json.loads(msg.value().decode('utf-8'))
        print(f"Received event: {event}")

        for recipient in event["recipients"]:
            send_email(recipient, event["subject"], event["body"])

except KeyboardInterrupt:
    print("Shutting down consumer...")

finally:
    consumer.close()
