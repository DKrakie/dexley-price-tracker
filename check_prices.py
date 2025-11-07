import requests
from bs4 import BeautifulSoup
import json
import os
import re

# Files
CONFIG_FILE = "config.json"
SEEN_FILE = ".last_prices.json"

# Discord webhook from GitHub secret
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
if not DISCORD_WEBHOOK_URL:
    raise ValueError("DISCORD_WEBHOOK_URL secret not set!")

# Staples URLs for Dexley chairs
STAPLES_URLS = [
    "https://www.staples.com/Staples-Dexley-Mesh-Task-Chair-Black-53293/product_24328579",
    "https://www.staples.com/Staples-Dexley-Ergonomic-Mesh-Task-Chair-Grey-57144/product_24423222",
    "https://www.staples.com/Staples-Dexley-Ergonomic-Mesh-Task-Chair-Black-53293CC/product_24423221"
]

# Load config
def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {"price_threshold": 150}
    with open(CONFIG_FILE) as f:
        return json.load(f)

# Load last seen prices
def load_seen():
    if not os.path.exists(SEEN_FILE):
        return {}
    with open(SEEN_FILE) as f:
        try:
            return json.load(f)
        except:
            return {}

# Save last seen prices
def save_seen(seen):
    with open(SEEN_FILE, "w") as f:
        json.dump(seen, f, indent=2)

# Scrape price from Staples page
def scrape_price(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url, headers=headers)
    soup = BeautifulSoup(r.text, "html.parser")

    # Try normal selectors
    price_tag = soup.select_one('[data-automation="product-price"]')
    if not price_tag:
        price_tag = soup.find(class_="price")
    
    if price_tag:
        price_text = price_tag.get_text(strip=True)
        price_text = re.sub(r"[^\d.]", "", price_text)
        try:
            return float(price_text)
        except:
            return None

    # Fallback: check for JSON embedded in page
    scripts = soup.find_all("script", type="application/ld+json")
    for s in scripts:
        try:
            data = json.loads(s.string)
            if isinstance(data, dict) and "offers" in data:
                price = data["offers"].get("price")
                if price:
                    return float(price)
        except:
            continue
    return None

# Send Discord alert
def send_alert(name, old_price, new_price, url):
    if old_price is None:
        msg = f"💺 **{name}** is now **${new_price:.2f}**!"
    elif new_price < old_price:
        msg = f"💺 **{name}** dropped from **${old_price:.2f} → ${new_price:.2f}!**"
    else:
        return
    msg += f"\n🔗 {url}"
    print("Sending to Discord:", msg)
    requests.post(DISCORD_WEBHOOK_URL, json={"content": msg})

# Main
if __name__ == "__main__":
    config = load_config()
    threshold = config.get("price_threshold", 150)
    seen = load_seen()

    print(f"Price threshold: ${threshold}")

    for url in STAPLES_URLS:
        # Get product title
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers)
        soup = BeautifulSoup(r.text, "html.parser")
        title_tag = soup.find("h1")
        name = title_tag.get_text(strip=True) if title_tag else url

        price = scrape_price(url)
        print(f"DEBUG: {name} -> {price}")

        if price is None:
            print(f"WARNING: Could not find price for {name}")
            continue

        old_price = seen.get(name)
        if price <= threshold and (old_price is None or price != old_price):
            send_alert(name, old_price, price, url)

        seen[name] = price

    save_seen(seen)
    print("✅ Scan complete.")
