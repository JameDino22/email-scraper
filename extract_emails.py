
from flask import Flask, request, jsonify
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from playwright.sync_api import sync_playwright
import re

app = Flask(__name__)

def extract_emails(text):
    patterns = [
        r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",
        r"[a-zA-Z0-9_.+-]+\s?\[at\]\s?[a-zA-Z0-9-]+\s?\[dot\]\s?[a-zA-Z0-9-.]+"
    ]
    emails = []
    for pattern in patterns:
        found = re.findall(pattern, text, re.I)
        for email in found:
            email = email.replace('[at]', '@').replace('[dot]', '.').replace(' ', '')
            if email not in emails:
                emails.append(email)
    return emails

def fetch_html_with_js(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, timeout=30000)
        page.wait_for_timeout(3000)
        html = page.content()
        browser.close()
        return html

def crawl_and_extract(url):
    emails = set()
    visited = set()
    pages_to_check = [url]

    for page_url in pages_to_check:
        try:
            html = fetch_html_with_js(page_url)
            soup = BeautifulSoup(html, "html.parser")
            emails.update(extract_emails(html))

            for link in soup.find_all("a", href=True):
                href = link["href"]
                if "mailto:" in href:
                    emails.add(href.replace("mailto:", ""))
                elif any(p in href for p in ["/contact", "/about", "/team"]):
                    full_url = urljoin(url, href)
                    if full_url not in visited and urlparse(full_url).netloc == urlparse(url).netloc:
                        visited.add(full_url)
                        pages_to_check.append(full_url)

        except Exception:
            continue

    return list(emails)

@app.route('/extract-emails', methods=['POST'])
def get_emails():
    data = request.get_json()
    url = data.get("url")
    if not url:
        return jsonify({"error": "No URL provided"}), 400
    emails = crawl_and_extract(url)
    return jsonify({"emails": emails})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
