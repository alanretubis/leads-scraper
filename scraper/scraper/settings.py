import os
import sys
import django

# --- DJANGO SETUP ---
# Ensure these paths are correct relative to your script location
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))
os.environ['DJANGO_SETTINGS_MODULE'] = 'manager.settings'
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
django.setup()

# --- SCRAPY GENERAL SETTINGS ---
BOT_NAME = 'scraper'
SPIDER_MODULES = ['scraper.spiders']
NEWSPIDER_MODULE = 'scraper.spiders'

# --- ETHICAL CONFIGURATION ---
ROBOTSTXT_OBEY = False 
USER_AGENT = 'LeadGenBot/1.0 (+http://yourwebsite.com; contact@yourdomain.com)'

# --- CONCURRENCY & RATE LIMITING ---
# Playwright is resource-intensive; high concurrency causes "Target Closed" errors.
CONCURRENT_REQUESTS = 8
CONCURRENT_REQUESTS_PER_DOMAIN = 4

AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 5.0
AUTOTHROTTLE_MAX_DELAY = 60.0
AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0

CLOSESPIDER_PAGECOUNT = 50

# --- PLAYWRIGHT & ASYNC CONFIGURATION ---
# This MUST be defined to handle the async nature of Playwright
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"

DOWNLOAD_HANDLERS = {
    "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
    "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
}

# Stability Fixes for Playwright
PLAYWRIGHT_BROWSER_TYPE = "chromium"
PLAYWRIGHT_LAUNCH_OPTIONS = {
    "headless": True,
    "args": [
        "--no-sandbox", 
        "--disable-dev-shm-usage", # Prevents crashes in Linux environments
        "--disable-gpu"
    ],
}

# Increase timeouts to prevent "Target Closed" during slow page loads
PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT = 60000  # 60 seconds

# --- PIPELINES ---
ITEM_PIPELINES = {
    'scraper.pipelines.DjangoLeadPipeline': 300,
}

# --- LOGGING (Optional but helpful for debugging) ---
LOG_LEVEL = 'INFO'
