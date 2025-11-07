import requests
from bs4 import BeautifulSoup
import json
import os

CONFIG_FILE = "config.json"
SEEN_FILE = "seen.json"
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
STAPLES_URL = "https://www.staples.com/search?query=dexley+chair"

# === Load Config ===
def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {"price_threshold": 150}
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

# === Load Seen Items ===
def load_seen():
    if not os.path.exists(SEEN_FILE):
        return set()
    with open(SEEN_FILE, "r") as f:
        try:
            return set(json.load(f))
        except:
            return set()

# === Save Seen Items ===
def save_seen(seen):
    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen), f)

# === Scrape Prices ===
def check_prices(price_limit):
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(STAPLES_URL, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")

    results = []
    for item in soup.select("div[data-automation='product-list'] div.product-card"):
        title_tag = item.select_one("a[data-automation='product-title']")
        price_tag = item.select_one("span[data-automation='product-price']")

        if not title_tag or not price_tag:
            continue

        name = title_tag.text.strip()
        price_text = price_tag.text.strip().replace("$", "").replace(",", "")
        try:
            price = float(price_text)
        except:
            continue

        link = "https://www.staples.com" + title_tag["href"]

        if price < price_limit:
            results.append((name, price, link))
    return results

# === Send to Discord ===
def send_discord_alert(items):
    for name, price, link in items:
        message = {
            "content": f"💺 **{name}** is now **${price:.2f}**!\n🔗 {link}"
        }
        requests.post(DISCORD_WEBHOOK_URL, json=message)

# === Main Logic ===
if __name__ == "__main__":
    config = load_config()
    price_limit = config.get("price_threshold", 150)
    seen = load_seen()

    deals = check_prices(price_limit)

    new_deals = []
    for name, price, link in deals:
        key = f"{name}-{price}"
        if key not in seen:
            new_deals.append((name, price, link))
            seen.add(key)

    if new_deals:
        send_discord_alert(new_deals)
        save_seen(seen)
        print(f"Sent {len(new_deals)} new alerts.")
    else:
        print("No new deals below threshold.")
