from flask import Flask, Response
import feedparser, requests, os
from datetime import datetime
import xml.etree.ElementTree as ET

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

ET.register_namespace('content', "http://purl.org/rss/1.0/modules/content/")

# -----------------------------
# AI + IMAGE HELPERS
# -----------------------------
def rewrite(text):
    """AI rewrite using Hugging Face"""
    if not HF_TOKEN:
        return text
    try:
        res = requests.post(
            HF_API,
            headers={"Authorization": f"Bearer {HF_TOKEN}"},
            json={"inputs": f"Rewrite this text in an SEO-friendly, natural human style:\n\n{text}"}
        )
        data = res.json()
        if isinstance(data, list) and len(data) > 0:
            rewritten = data[0].get("generated_text", "")
            return rewritten.strip() or text
    except Exception as e:
        print("AI Error:", e)
    return text


def get_image(query):
    """Fallback Unsplash image if none found in feed"""
    if not UNSPLASH_KEY:
        return None
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
# RSS GENERATION
# -----------------------------
def generate_rss(category):
    feeds = CATEGORIES.get(category.lower())
    if not feeds:
        return None

    rss = ET.Element("rss", {
        "version": "2.0",
        "xmlns:content": "http://purl.org/rss/1.0/modules/content/"
    })
    channel = ET.SubElement(rss, "channel")

    ET.SubElement(channel, "title").text = f"AI Generated RSS - {category.title()}"
    ET.SubElement(channel, "link").text = f"https://storycircle.store/rss/{category}"
    ET.SubElement(channel, "description").text = f"AI rewritten feed for {category.title()} news."
    ET.SubElement(channel, "language").text = "en"

    for feed_url in feeds:
        f = feedparser.parse(feed_url)
        for entry in f.entries[:4]:
            item = ET.SubElement(channel, "item")
            ET.SubElement(item, "title").text = entry.title
            ET.SubElement(item, "link").text = entry.link
            ET.SubElement(item, "guid").text = entry.link + "#ai"
            ET.SubElement(item, "pubDate").text = datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0000")

            # --- Description ---
            summary = getattr(entry, "summary", "")
            if hasattr(entry, "content") and len(entry.content) > 0:
                summary = entry.content[0].value
            rewritten = rewrite(summary)

            desc = ET.SubElement(item, "description")
            desc.text = f"<![CDATA[{rewritten[:500]}]]>"

            content_encoded = ET.SubElement(item, "{http://purl.org/rss/1.0/modules/content/}encoded")
            content_encoded.text = f"<![CDATA[{rewritten}]]>"

            # --- Image (prefer original) ---
            img_url = None
            if hasattr(entry, "media_content") and entry.media_content:
                img_url = entry.media_content[0].get("url")
            elif hasattr(entry, "links"):
                for link in entry.links:
                    if link.get("type", "").startswith("image"):
                        img_url = link.get("href")
                        break
            if not img_url:
                img_url = get_image(entry.title)
            if img_url:
                ET.SubElement(item, "enclosure", {"url": img_url, "type": "image/jpeg"})

    xml_str = ET.tostring(rss, encoding="utf-8", xml_declaration=True)
    return xml_str


# -----------------------------
# ROUTES
# -----------------------------
@app.route("/")
def index():
    return "✅ AI RSS Generator running: /rss/tech /rss/business /rss/sports /rss/health /rss/entertainment"

@app.route("/rss/<category>")
def feed(category):
    xml = generate_rss(category)
    if xml:
        return Response(xml, mimetype="application/rss+xml")
    return Response("Category not found", status=404)

# -----------------------------
# RUN
# -----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
