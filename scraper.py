import os
import time
import threading
from flask import Flask
import requests
from bs4 import BeautifulSoup

# Flask অ্যাপ তৈরি (Render এর পোর্ট চেকিং সন্তুষ্ট করার জন্য)
app = Flask(__name__)

@app.route('/')
def home():
    return "Scraper is running!", 200

# আপনার দেওয়া বটের টোকেন এবং চ্যাট আইডি
TELEGRAM_TOKEN = "8906640720:AAHq41Lna_ROMeLRoUAQ4liXMdzXTXm94kw"
TELEGRAM_CHAT_ID = "6382850126" 
URL = "http://tmed.gov.bd/pages/notices"

last_sent_link = None

def get_latest_notices():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        response = requests.get(URL, headers=headers, timeout=15)
        response.encoding = 'utf-8'
        
        if response.status_code != 200:
            print(f"Failed to fetch webpage. Status: {response.status_code}")
            return []
        
        soup = BeautifulSoup(response.text, "html.parser")
        table = soup.find("table")
        if not table:
            print("Notice table not found.")
            return []
            
        rows = table.find_all("tr")[1:]
        notices = []
        
        for row in rows:
            cols = row.find_all("td")
            if len(cols) >= 2:
                a_tag = cols[1].find("a")
                if a_tag:
                    title = a_tag.text.strip()
                    link = a_tag.get("href", "")
                    if link.startswith("/"):
                        link = "http://tmed.gov.bd" + link
                    date = cols[0].text.strip() if len(cols) > 0 else ""
                    notices.append({"title": title, "link": link, "date": date})
        
        return notices
    except Exception as e:
        print(f"Error scraping website: {e}")
        return []

def send_telegram_message(message):
    telegram_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(telegram_url, json=payload, timeout=10)
        if response.status_code != 200:
            print(f"Telegram API Error: {response.text}")
    except Exception as e:
        print(f"Failed to send Telegram message: {e}")

# স্ক্র্যাপারের মূল লুপ (যা ব্যাকগ্রাউন্ডে চলবে)
def monitor_website():
    global last_sent_link
    print("Background scraper thread started...")
    
    # Render-এ ডেপ্লয় হওয়ার সাথে সাথেই আপনাকে সচল হওয়ার কনফার্মেশন মেসেজ পাঠাবে
    send_telegram_message("🚀 *টিএমইডি স্ক্র্যাপার সফলভাবে চালু হয়েছে এবং ব্যাকগ্রাউন্ডে প্রতি ৫ মিনিট পর পর নোটিশ চেক করছে!*")
    
    while True:
        notices = get_latest_notices()
        if notices:
            latest_notice = notices[0]
            
            # প্রথমবার রান করার সময় শুধু লিংকটি সেভ করবে
            if last_sent_link is None:
                last_sent_link = latest_notice["link"]
                print(f"Initial setup complete. Saved latest notice link: {last_sent_link}")
            
            # যদি নতুন কোনো নোটিশ আসে
            elif latest_notice["link"] != last_sent_link:
                message = (
                    f"🔔 *টিএমইডি নতুন নোটিশ!* 🔔\n\n"
                    f"📌 *শিরোনাম:* {latest_notice['title']}\n"
                    f"📅 *তারিখ:* {latest_notice['date']}\n"
                    f"🔗 *লিংক:* [এখানে ক্লিক করুন]({latest_notice['link']})"
                )
                send_telegram_message(message)
                print("New notice sent to Telegram!")
                last_sent_link = latest_notice["link"]
            else:
                print("No new notice found.")
        else:
            print("Could not retrieve notices this time.")
            
        # ৫ মিনিট (৩০০ সেকেন্ড) পর পর চেক করার টাইম ডিলে
        print("Waiting for 5 minutes...")
        time.sleep(300)

if __name__ == "__main__":
    # স্ক্র্যাপারটিকে আলাদা থ্রেডে ব্যাকগ্রাউন্ডে চালু করা
    scraper_thread = threading.Thread(target=monitor_website)
    scraper_thread.daemon = True
    scraper_thread.start()
    
    # Render-এর পোর্ট বাইন্ডিং ঠিক রাখার জন্য Flask সার্ভার চালু করা
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
