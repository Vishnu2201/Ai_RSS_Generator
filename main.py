from flask import Flask, Response
import feedparser, requests, os, html, re
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
# HELPERS
# -----------------------------
def clean_html(raw_html):
    """Remove HTML tags and entities for plain text descriptions."""
    text = re.sub(r"<[^>]+>", "", raw_html)
    text = html.unescape(text)
    return text.strip()


def rewrite(text, mode="content"):
    """Rewrite title or content using Hugging Face AI."""
    if not HF_TOKEN:
        return html.unescape(text)
    if mode == "title":
        prompt = f"Rewrite this news title to be more engaging and SEO-friendly:\n\n{text}"
    else:
        prompt = (
            "Rewrite this article into a detailed, SEO-optimized summary (3–4 paragraphs), "
            "formatted as valid HTML with proper paragraphs and a professional tone:\n\n" + text
        )
    try:
        res = requests.post(
            HF_API,
            headers={"Authorization": f"Bearer {HF_TOKEN}"},
            json={"inputs": prompt}
        )
        data = res.json()
        if isinstance(data, list) and len(data) > 0:
            rewritten = data[0].get("generated_text", "").strip()
            return html.unescape(rewritten)
    except Exception as e:
        print("AI Rewrite Error:", e)
    return html.unescape(text)


def get_image(query):
    """Fetch Unsplash image if none found in feed."""
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
        for entry in f.entries[:5]:
            item = ET.SubElement(channel, "item")

            # Title
            title = rewrite(entry.title, mode="title")
            ET.SubElement(item, "title").text = title
            ET.SubElement(item, "link").text = entry.link
            ET.SubElement(item, "guid").text = entry.link + "#ai"
            ET.SubElement(item, "pubDate").text = datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0000")

            # Content
            raw_summary = getattr(entry, "summary", "")
            if hasattr(entry, "content") and len(entry.content) > 0:
                raw_summary = entry.content[0].value
            rewritten_html = rewrite(raw_summary, mode="content")
            rewritten_html = html.unescape(rewritten_html)
            plain_text = clean_html(rewritten_html)

            # Description (plain text for CMS)
            desc = ET.SubElement(item, "description")
            desc.text = f"<![CDATA[{plain_text[:800]}]]>"

            # Full Content
            content_encoded = ET.SubElement(item, "{http://purl.org/rss/1.0/modules/content/}encoded")
            content_encoded.text = f"<![CDATA[{rewritten_html}<br><br><i>Source: <a href='{entry.link}'>{entry.link}</a></i>]]>"

            # Optional Author
            ET.SubElement(item, "author").text = "AI Writer"

            # Image
            img_url = None
            if hasattr(entry, "media_content") and entry.media_content:
                img_url = entry.media_content[0].get("url")
            elif hasattr(entry, "links"):
                for link in entry.links:
                    if link.get("type", "").startswith("image"):
                        img_url = link.get("href")
                        break
            if not img_url:
                img_url = get_image(f"{category} {entry.title}")
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
