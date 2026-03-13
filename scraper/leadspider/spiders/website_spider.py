import json
import re

import scrapy
from scrapy.linkextractors import LinkExtractor

from leadspider.items import ScrapedWebsite

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")

PLACEHOLDER_EMAILS = {
    "info@example.com",
    "test@example.com",
    "email@example.com",
    "name@example.com",
    "your@email.com",
    "user@example.com",
    "admin@example.com",
}

CONTACT_LINK_RE = re.compile(
    r"impressum|kontakt|contact|legal[\-_\s]?notice|about[\-_\s]?us|ueber[\-_\s]?uns",
    re.IGNORECASE,
)


class WebsiteSpider(scrapy.Spider):
    name = "website_spider"

    def __init__(self, urls_file: str = "", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_urls_list: list[str] = []
        if urls_file:
            with open(urls_file, "r") as f:
                self.start_urls_list = json.load(f)

    def start_requests(self):
        for url in self.start_urls_list:
            if not url.startswith(("http://", "https://")):
                url = f"https://{url}"
            yield scrapy.Request(
                url,
                callback=self.parse,
                errback=self.handle_error,
                meta={"playwright": True, "playwright_page_methods": [], "original_url": url},
                dont_filter=True,
            )

    def parse(self, response):
        original_url = response.meta.get("original_url", response.url)
        body_text = self._extract_visible_text(response)
        emails = self._extract_emails(response.text)

        if emails:
            yield ScrapedWebsite(url=original_url, email=emails[0], body_text=body_text)
            return

        # No email found — try contact/impressum pages
        link_extractor = LinkExtractor(
            allow=CONTACT_LINK_RE,
            unique=True,
        )
        links = link_extractor.extract_links(response)

        if links:
            yield scrapy.Request(
                links[0].url,
                callback=self.parse_contact,
                errback=self.handle_error,
                meta={
                    "playwright": True,
                    "playwright_page_methods": [],
                    "original_url": original_url,
                    "body_text": body_text,
                },
                dont_filter=True,
            )
        else:
            yield ScrapedWebsite(url=original_url, email=None, body_text=body_text)

    def parse_contact(self, response):
        original_url = response.meta["original_url"]
        body_text = response.meta.get("body_text", "")
        emails = self._extract_emails(response.text)

        # Append contact page text to homepage text
        contact_text = self._extract_visible_text(response)
        combined_text = (body_text + " " + contact_text)[:1500]

        yield ScrapedWebsite(
            url=original_url,
            email=emails[0] if emails else None,
            body_text=combined_text,
        )

    def handle_error(self, failure):
        request = failure.request
        original_url = request.meta.get("original_url", request.url)
        self.logger.warning("Request failed for %s: %s", original_url, failure.getErrorMessage())
        yield ScrapedWebsite(url=original_url, email=None, body_text="")

    @staticmethod
    def _extract_visible_text(response) -> str:
        # Remove script/style tags then get text
        body = response.css("body")
        if not body:
            return ""
        # Remove script and style elements
        texts = body.css("*:not(script):not(style):not(noscript)::text").getall()
        clean = " ".join(t.strip() for t in texts if t.strip())
        return clean[:1000]

    @staticmethod
    def _extract_emails(html: str) -> list[str]:
        found = EMAIL_RE.findall(html)
        # Filter out placeholders and image file extensions
        valid = []
        for email in found:
            lower = email.lower()
            if lower in PLACEHOLDER_EMAILS:
                continue
            if lower.endswith((".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp")):
                continue
            valid.append(email)
        return valid
