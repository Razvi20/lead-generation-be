BOT_NAME = "leadspider"

SPIDER_MODULES = ["leadspider.spiders"]
NEWSPIDER_MODULE = "leadspider.spiders"

# --- Playwright integration ---
DOWNLOAD_HANDLERS = {
    "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
    "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
}
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"

PLAYWRIGHT_BROWSER_TYPE = "chromium"
PLAYWRIGHT_LAUNCH_OPTIONS = {"headless": True}

# --- Concurrency ---
CONCURRENT_REQUESTS = 4
DOWNLOAD_DELAY = 1
CONCURRENT_REQUESTS_PER_DOMAIN = 2

# --- Timeouts ---
DOWNLOAD_TIMEOUT = 15

# --- Politeness ---
ROBOTSTXT_OBEY = True
USER_AGENT = "LeadGenBot/1.0 (+https://example.com/bot)"

# --- Logging ---
LOG_LEVEL = "INFO"

# --- Feed export (overridden via CLI -o flag) ---
FEED_EXPORT_ENCODING = "utf-8"

# --- Misc ---
REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
