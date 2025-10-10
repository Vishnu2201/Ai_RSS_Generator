from flask import Flask, Response
import feedparser, requests, os
from datetime import datetime
from xml.sax.saxutils import escape

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
    """Rewrite text using Hugging Face API (SEO-friendly)."""
    try:
        if not HF_TOKEN:
            return text
        res = requests.post(
            HF_API,
            headers={"Authorization": f"Bearer {HF_TOKEN}"},
            json={"inputs": f"Rewrite this article in a natural, SEO-friendly tone:\n\n{text}"}
        )
        data = res.json()
        if isinstance(data, list) and len(data) > 0:
            rewritten = data[0].get("generated_text", "").strip()
            if rewritten:
                return rewritten
    except Exception as e:
        print("AI Error:", e)
    return text or "No content available"

def get_image(query):
    """Get fallback Unsplash image if feed has none."""
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

    xml = []
    xml.append('<?xml version="1.0" encoding="utf-8"?>')
    xml.append('<rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/">')
    xml.append("<channel>")
    xml.append(f"<title>AI Generated RSS - {escape(category.title())}</title>")
    xml.append(f"<link>https://storycircle.store/rss/{escape(category)}</link>")
    xml.append(f"<description>AI rewritten feed for {escape(category.title())} news.</description>")
    xml.append("<language>en</language>")

    for feed_url in feeds:
        f = feedparser.parse(feed_url)
        for entry in f.entries[:5]:
            title = escape(entry.title)
            link = entry.link
            summary = getattr(entry, "summary", entry.title)
            content = rewrite(summary)

            # Prefer original feed images
            img_url = None
            if hasattr(entry, "media_content") and entry.media_content:
                img_url = entry.media_content[0].get("url")
            elif hasattr(entry, "links"):
                for link_obj in entry.links:
                    if link_obj.get("type", "").startswith("image"):
                        img_url = link_obj.get("href")
                        break
            if not img_url:
                img_url = get_image(title)

            # Write <item>
            xml.append("<item>")
            xml.append(f"<title>{title}</title>")
            xml.append(f"<link>{link}</link>")
            xml.append(f"<guid>{link}#ai</guid>")
            xml.append(f"<pubDate>{datetime.now().strftime('%a, %d %b %Y %H:%M:%S +0000')}</pubDate>")

            # Proper CDATA (not escaped)
            xml.append(f"<![CDATA[{content[:500]}]]>")
            xml.append(f"<description><![CDATA[{content[:500]}]]></description>")
            xml.append(f"<content:encoded><![CDATA[{content}]]></content:encoded>")

            if img_url:
                xml.append(f'<enclosure url="{img_url}" type="image/jpeg" />')

            xml.append("</item>")

    xml.append("</channel></rss>")
    return "\n".join(xml)

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
