import requests
from bs4 import BeautifulSoup
import json
import os

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
STAPLES_URL = "https://www.staples.com/search?query=dexley+chair"
PRICE_THRESHOLD = 150

def check_prices():
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

        if price < PRICE_THRESHOLD:
            results.append((name, price, link))
    return results

def send_discord_alert(items):
    for name, price, link in items:
        message = {
            "content": f"💺 **{name}** is now **${price:.2f}**!\n🔗 {link}"
        }
        requests.post(DISCORD_WEBHOOK_URL, json=message)

if __name__ == "__main__":
    deals = check_prices()
    if deals:
        send_discord_alert(deals)
    else:
        print("No Dexley chairs under ${}".format(PRICE_THRESHOLD))
