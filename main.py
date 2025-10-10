from flask import Flask, Response
import feedparser, requests, os
from datetime import datetime
from xml.etree.ElementTree import Element, SubElement, tostring

# ✅ Define Flask app first
app = Flask(__name__)

# -----------------------------
# CONFIG
# -----------------------------
CATEGORIES = {
    "tech": [
        "https://techcrunch.com/feed/",
        "https://www.theverge.com/rss/index.xml",
        "https://www.wired.com/feed/rss"
    ],
    "business": [
        "https://www.cnbc.com/id/10001147/device/rss/rss.html",
        "https://www.financialexpress.com/feed/",
        "https://economictimes.indiatimes.com/rssfeedsdefault.cms"
    ],
    "sports": [
        "https://timesofindia.indiatimes.com/rssfeeds913168846.cms",
        "https://www.espn.com/espn/rss/news",
        "https://feeds.bbci.co.uk/sport/rss.xml"
    ],
    "health": [
        "https://www.medicalnewstoday.com/rss",
        "https://rssfeeds.webmd.com/rss/rss.aspx?RSSSource=RSS_PUBLIC"
    ],
    "entertainment": [
        "https://variety.com/feed/",
        "https://www.hollywoodreporter.com/t/feed/",
        "https://www.ndtv.com/entertainment/rss"
    ]
}

HF_TOKEN = os.getenv("HF_TOKEN")
HF_API = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct"
UNSPLASH_KEY = os.getenv("UNSPLASH_KEY")

# -----------------------------
# AI + IMAGE HELPERS
# -----------------------------
def rewrite(text):
    try:
        res = requests.post(
            HF_API,
            headers={"Authorization": f"Bearer {HF_TOKEN}"},
            json={"inputs": f"Rewrite this article in a natural, SEO-friendly, human tone:\n\n{text}"}
        )
        data = res.json()
        if isinstance(data, list) and len(data) > 0:
            return data[0].get("generated_text", "")
    except Exception as e:
        print("AI Error:", e)
    return text


def get_image(query):
    try:
        res = requests.get(
            f"https://api.unsplash.com/photos/random?query={query}&orientation=landscape",
            headers={"Authorization": f"Client-ID {UNSPLASH_KEY}"}
        )
        d = res.json()
        if "urls" in d:
            return d["urls"]["regular"]
    except Exception as e:
        print("Image error:", e)
    return None

# -----------------------------
# RSS GENERATION LOGIC
# -----------------------------
def generate_rss(category):
    feeds = CATEGORIES.get(category.lower())
    if not feeds:
        return None

    root = Element("rss", version="2.0")
    channel = SubElement(root, "channel")

    SubElement(channel, "title").text = f"AI Generated RSS - {category.title()}"
    SubElement(channel, "link").text = f"https://yourapp.onrender.com/rss/{category}"
    SubElement(channel, "description").text = f"AI rewritten feed for {category.title()} news."

    for feed_url in feeds:
        f = feedparser.parse(feed_url)
        for entry in f.entries[:3]:
            item = SubElement(channel, "item")
            SubElement(item, "title").text = entry.title
            SubElement(item, "link").text = entry.link

            content = rewrite(entry.summary if hasattr(entry, "summary") else entry.title)
            desc = SubElement(item, "description")
            desc.text = f"<![CDATA[{content}]]>"

            img_url = get_image(entry.title.split()[0])
            if img_url:
                SubElement(item, "enclosure", url=img_url, type="image/jpeg")

            SubElement(item, "pubDate").text = datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0000")
            SubElement(item, "guid").text = entry.link + "#ai"

    xml = tostring(root, encoding="utf-8")
    return xml

# -----------------------------
# ROUTES
# -----------------------------
@app.route("/")
def index():
    return "✅ AI RSS Generator is running. Feeds: /rss/tech, /rss/business, /rss/sports, /rss/health, /rss/entertainment"

@app.route("/rss/<category>")
def category_feed(category):
    xml = generate_rss(category)
    if xml:
        return Response(xml, mimetype="application/rss+xml")
    else:
        return Response(f"Category '{category}' not found.", status=404)

@app.route("/refresh")
def refresh_all():
    print("🔁 Refreshing all categories...")
    for category in CATEGORIES.keys():
        try:
            _ = generate_rss(category)
            print(f"✅ Refreshed {category}")
        except Exception as e:
            print(f"⚠️ Error refreshing {category}: {e}")
    return "All categories refreshed successfully!"

# -----------------------------
# RUN
# -----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
