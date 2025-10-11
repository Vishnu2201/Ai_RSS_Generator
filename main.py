from flask import Flask, Response
import feedparser, requests, os, html, re
from datetime import datetime
import xml.dom.minidom as minidom
import xml.etree.ElementTree as ET

app = Flask(__name__)

# -----------------------------
# CONFIG
# -----------------------------
CATEGORIES = {
    "entertainment": [
        "https://variety.com/feed/",
        "https://www.hollywoodreporter.com/t/feed/",
        "https://www.ndtv.com/entertainment/rss"
    ],
    "tech": [
        "https://techcrunch.com/feed/",
        "https://www.theverge.com/rss/index.xml",
        "https://www.wired.com/feed/rss"
    ],
    "business": [
        "https://economictimes.indiatimes.com/rssfeedsdefault.cms",
        "https://www.cnbc.com/id/10001147/device/rss/rss.html"
    ]
}

HF_TOKEN = os.getenv("HF_TOKEN")
HF_API = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct"
UNSPLASH_KEY = os.getenv("UNSPLASH_KEY")

ET.register_namespace('dc', "http://purl.org/dc/elements/1.1/")
ET.register_namespace('atom', "http://www.w3.org/2005/Atom")

# -----------------------------
# HELPERS
# -----------------------------
def clean_html(raw_html):
    text = re.sub(r"<[^>]+>", "", raw_html)
    return html.unescape(text.strip())


def rewrite(text, mode="content"):
    """Rewrite with Hugging Face."""
    if not HF_TOKEN:
        return html.unescape(text)
    prompt = f"Rewrite this {'headline' if mode=='title' else 'article'} in a clear, natural tone with SEO-friendly language:\n\n{text}"
    try:
        res = requests.post(
            HF_API,
            headers={"Authorization": f"Bearer {HF_TOKEN}"},
            json={"inputs": prompt}
        )
        data = res.json()
        if isinstance(data, list) and len(data) > 0:
            return html.unescape(data[0].get("generated_text", text))
    except Exception as e:
        print("AI Rewrite Error:", e)
    return html.unescape(text)


def get_image(query):
    if not UNSPLASH_KEY:
        return None
    try:
        r = requests.get(
            f"https://api.unsplash.com/photos/random?query={query}&orientation=landscape",
            headers={"Authorization": f"Client-ID {UNSPLASH_KEY}"}
        )
        j = r.json()
        if "urls" in j:
            return j["urls"]["regular"]
    except Exception as e:
        print("Unsplash error:", e)
    return None


# -----------------------------
# RSS GENERATION
# -----------------------------
def generate_rss(category):
    feeds = CATEGORIES.get(category.lower())
    if not feeds:
        return None

    # NOTE: Do NOT pre-register namespaces (ElementTree will handle automatically)
    rss = ET.Element("rss", {
        "version": "2.0",
        "xmlns:dc": "http://purl.org/dc/elements/1.1/",
        "xmlns:atom": "http://www.w3.org/2005/Atom"
    })
    channel = ET.SubElement(rss, "channel")

    # --- Feed metadata ---
    ET.SubElement(channel, "{http://www.w3.org/2005/Atom}link", {
        "href": f"https://storycircle.store/rss/{category}",
        "rel": "self",
        "type": "application/rss+xml"
    })
    ET.SubElement(channel, "title").text = f"StoryCircle - {category.title()} News"
    ET.SubElement(channel, "link").text = "https://storycircle.store"
    ET.SubElement(channel, "description").text = f"AI rewritten {category.title()} stories from top news outlets."
    ET.SubElement(channel, "language").text = "en"
    ET.SubElement(channel, "copyright").text = "© 2025 StoryCircle News Aggregator"
    ET.SubElement(channel, "docs").text = "https://storycircle.store/about"

    image = ET.SubElement(channel, "image")
    ET.SubElement(image, "title").text = "StoryCircle"
    ET.SubElement(image, "link").text = "https://storycircle.store"
    ET.SubElement(image, "url").text = "https://storycircle.store/static/logo.png"

    # --- Entries ---
    for feed_url in feeds:
        f = feedparser.parse(feed_url)
        for entry in f.entries[:6]:
            item = ET.SubElement(channel, "item")

            title = rewrite(entry.title, mode="title")
            summary = getattr(entry, "summary", "")
            if hasattr(entry, "content") and entry.content:
                summary = entry.content[0].value
            rewritten = rewrite(summary)
            clean_summary = clean_html(rewritten)

            ET.SubElement(item, "title").text = title
            desc = ET.SubElement(item, "description")
            desc.text = f"<![CDATA[{clean_summary[:850]}]]>"
            ET.SubElement(item, "link").text = entry.link
            ET.SubElement(item, "guid").text = entry.link
            ET.SubElement(item, "pubDate").text = datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0530")
            ET.SubElement(item, "{http://purl.org/dc/elements/1.1/}creator").text = "StoryCircle AI Writer"

            # Image
            img_url = None
            if hasattr(entry, "media_content") and entry.media_content:
                img_url = entry.media_content[0].get("url")
            elif hasattr(entry, "links"):
                for l in entry.links:
                    if l.get("type", "").startswith("image"):
                        img_url = l.get("href")
                        break
            if not img_url:
                img_url = get_image(title)
            if img_url:
                ET.SubElement(item, "enclosure", {
                    "url": img_url,
                    "type": "image/jpeg",
                    "length": "0"
                })

    # Pretty-print XML
    rough_string = ET.tostring(rss, "utf-8")
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")



# -----------------------------
# ROUTES
# -----------------------------
@app.route("/")
def index():
    return "✅ RSS Feed generator ready. Try /rss/entertainment or /rss/tech"


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
