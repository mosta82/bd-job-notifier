import json
import os
import requests
from html.parser import HTMLParser
from urllib.parse import urljoin


class JobLinkParser(HTMLParser):
  def __init__(self):
    super().__init__()
    self.links = []
    self._href = None
    self._text = []

  def handle_starttag(self, tag, attrs):
    if tag == "a":
      self._href = dict(attrs).get("href")
      self._text = []

  def handle_data(self, data):
    if self._href is not None:
      self._text.append(data)

  def handle_endtag(self, tag):
    if tag == "a" and self._href is not None:
      self.links.append((" ".join(self._text).strip(), self._href))
      self._href = None
      self._text = []

# Configuration
TARGET_URL = "https://bdgovtjob.net/"
SENT_JOBS_FILE = "sent_jobs.json"

# Telegram bot configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


def load_sent_jobs():
  if os.path.exists(SENT_JOBS_FILE):
    with open(SENT_JOBS_FILE, "r", encoding="utf-8") as f:
      return json.load(f)
  return []


def save_sent_jobs(sent_jobs):
  with open(SENT_JOBS_FILE, "w", encoding="utf-8") as f:
    json.dump(sent_jobs, f, ensure_ascii=False, indent=4)


def send_telegram_message(message):
  if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
    print("Telegram configuration is missing.")
    return

  url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
  payload = {
      "chat_id": TELEGRAM_CHAT_ID,
      "text": message,
      "parse_mode": "Markdown",
  }
  response = requests.post(url, json=payload, timeout=15)
  if response.status_code == 200:
    print("Telegram notification sent successfully!")
  else:
    print(f"Failed to send Telegram message. Status: {response.status_code}")


def check_jobs():
  print("Checking for new government jobs...")
  sent_jobs = load_sent_jobs()

  headers = {
      "User-Agent": (
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
          " like Gecko) Chrome/120.0.0.0 Safari/537.36"
      )
  }

  try:
    response = requests.get(TARGET_URL, headers=headers, timeout=15)
    if response.status_code != 200:
      print(f"Failed to fetch website. Status code: {response.status_code}")
      return

    parser = JobLinkParser()
    parser.feed(response.text)
    job_items = parser.links

    new_jobs_found = False

    for title, link in job_items:

      if title and link and ("Job Circular" in title or "নিয়োগ বিজ্ঞপ্তি" in title):
        link = urljoin(TARGET_URL, link)

        if link not in sent_jobs:
          print(f"Found new job: {title}")
          msg = (
              f"🚨 *নতুন সরকারি চাকরির খবর!*\n\n📌 *{title}*\n🔗 [বিস্তারিত"
              f" দেখুন]({link})"
          )

          # Send the message to Telegram
          send_telegram_message(msg)

          sent_jobs.append(link)
          new_jobs_found = True
          break

    if new_jobs_found:
      save_sent_jobs(sent_jobs)
    else:
      print("No new jobs found.")

  except Exception as e:
    print(f"An error occurred: {e}")


if __name__ == "__main__":
  check_jobs()
