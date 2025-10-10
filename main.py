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
