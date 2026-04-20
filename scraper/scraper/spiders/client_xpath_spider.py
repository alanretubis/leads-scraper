import scrapy
import urllib.parse
from scrapy import signals
from django.utils import timezone
from django.utils.dateparse import parse_date
from asgiref.sync import sync_to_async
from leads.models import TargetSite
import re
from datetime import datetime, timedelta

def parse_lead_status(text):
    text = (text or "").strip().lower()
    if any(token in text for token in ['closed', 'expired', 'filled', 'no longer hiring', 'not hiring', 'withdrawn']):
        return 'CLOSED'
    if any(token in text for token in ['hiring', 'open', 'accepting applications', 'apply now', 'actively recruiting']):
        return 'OPEN'
    return 'UNKNOWN'

def parse_posted_date(text):
    if not text:
        return None

    text = " ".join(text.split()).strip().lower()

    if 'today' in text:
        return timezone.now().date()
    if 'yesterday' in text:
        return (timezone.now() - timedelta(days=1)).date()

    rel_match = re.search(
        r'(?P<qty>\d+)\s+'
        r'(?P<unit>second|minute|hour|day|week|month|year)s?\s+ago',
        text
    )
    if rel_match:
        qty = int(rel_match.group('qty'))
        unit = rel_match.group('unit')
        if unit == 'second':
            delta = timedelta(seconds=qty)
        elif unit == 'minute':
            delta = timedelta(minutes=qty)
        elif unit == 'hour':
            delta = timedelta(hours=qty)
        elif unit == 'day':
            delta = timedelta(days=qty)
        elif unit == 'week':
            delta = timedelta(weeks=qty)
        elif unit == 'month':
            delta = timedelta(days=qty * 30)
        else:
            delta = timedelta(days=qty * 365)
        return (timezone.now() - delta).date()

    text = text.upper()
    match = re.search(r'(\d{4}-\d{2}-\d{2})', text)
    if match:
        return parse_date(match.group(1))

    match = re.search(r'(\d{1,2}/\d{1,2}/\d{2,4})', text)
    if match:
        for fmt in ("%m/%d/%Y", "%m/%d/%y"):
            try:
                return datetime.strptime(match.group(1), fmt).date()
            except ValueError:
                continue

    match = re.search(r'([A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4})', text)
    if match:
        date_text = match.group(1).replace(',', '')
        for fmt in ("%B %d %Y", "%b %d %Y"):
            try:
                return datetime.strptime(date_text, fmt).date()
            except ValueError:
                continue

    return None

def parse_work_setup(text):
    if not text: return None
    t = text.lower()
    if 'remote' in t: return 'Remote'
    if 'hybrid' in t: return 'Hybrid'
    if any(kw in t for kw in ['on-site', 'onsite', 'in person']): return 'On-site'
    return None

class ClientXpathSpider(scrapy.Spider):
    name = 'client_xpath_spider'

    async def start(self):

        @sync_to_async
        def set_pending():
            TargetSite.objects.filter(is_active=True).update(status='PENDING')
        await set_pending()
        
        """Fetch active targets and keywords from Django."""

        get_targets = sync_to_async(lambda: list(TargetSite.objects.filter(is_active=True)))
        targets = await get_targets()

        for target in targets:
            keyword_list = [k.strip() for k in (target.keywords or "").split(',') if k.strip()]
            
            if not keyword_list:
                yield self.make_request(target.base_url, target.id)
            else:
                for kw in keyword_list:

                    #URL Encode the keyword
                    safe_kw = urllib.parse.quote(kw)
                    
                    #Construct URL
                    search_url = target.url_template.format(keyword=safe_kw)
                    yield self.make_request(search_url,  target.id)

    def make_request(self, url, target_id):
        return scrapy.Request(
            url=url,
            callback=self.parse,
            meta={
                "playwright": True,
                "target_id": target_id,
                "playwright_page_methods": [
                    {"method": "wait_for_selector", "args": ['//article | //div[contains(@class, "job")]']},
                ],
            }
        )

    def parse(self, response):

        target_id = response.meta.get("target_id")
        self.logger.info(f"XPath Spider reaching: {response.url}")

        # Site-agnostic XPath selectors
        items = response.xpath('//div[contains(@class, "quote")] | //article | //div[contains(@class, "job")] | //li[contains(@class, "job")]')
        
        for item in items:

            item_html = item.get() or "" 

            relative_url = item.xpath('.//h3/a/@href | .//h4/a/@href | .//a[contains(@class, "link")]/@href | .//a/@href').get()
            exact_url = response.urljoin(relative_url) if relative_url else response.url

            raw_job_title = item.xpath(
            './/a[contains(@class, "jcs-JobTitle")]//span/text() | ' # Indeed specific
                './/h1//text() | '                                      # LinkedIn & Large headers
                './/h3/a/text() | '                                      # Standard card titles
                './/h3//text() | '                                       # Fallback text in H3
                './/h4/text() | '                                        # Smaller card titles
                './/a[contains(@class, "title")]//text() | '            # Class-based titles
                './/*[@id[contains(., "jobTitle")]]/text()'             # ID-based fallback
            ).get()

            job_title = raw_job_title.strip() if raw_job_title else "Unknown Position"

            company_name = item.xpath(
                './/a[contains(@href, "/company/")]/text() | '
                './/div[contains(@class, "company")]/text() | '
                './/span[contains(@class, "company")]/text() | '
                './/small[@class="author"]/text()'
            ).get()

            email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[A-Za-z]{2,}'
            found_emails = re.findall(email_pattern, item_html)
            email = found_emails[0] if found_emails else item.xpath('.//a[contains(@href, "mailto:")]/@href').re_first(r'mailto:([^?]+)')
        
            raw_name = item.xpath('.//small[@class="author"]/text() | .//h3/a/@title | .//h4/text() | .//h3/text() | .//a[contains(@class, "title")]/text()').get()

            raw_status_text = " ".join(item.xpath(
                './/*[contains(@class, "status")]/text() | '
                './/*[contains(text(), "Hiring") or contains(text(), "Closed") or contains(text(), "Expired") or contains(text(), "Filled")]/text()'
            ).getall())
            posted_text = " ".join(item.xpath(
                './/*[contains(@class, "date") or contains(@class, "posted") or contains(@class, "time")]/text() | '
                './/*[contains(text(), "Posted") or contains(text(), "ago")]/text()'
            ).getall())

            found_ws = {k for t in item.xpath('.//text()').getall() for k in ['remote', 'onsite', 'on-site', 'hybrid'] if k in t.lower()}
            raw_work_setup = ", ".join(found_ws)

            raw_location = " ".join(item.xpath(
                './/*[contains(@class, "location")]/text() | '
                './/*[contains(@class, "job-location")]/text() '
            ).getall())

            yield {
                'site_id': target_id,
                'name': company_name.strip() if company_name else "Unknown Company",
                'job_title': job_title.strip() if job_title else "Unknown Position",
                'email': email,
                'comment': item.xpath('.//span[@class="text"]/text() | .//div[contains(@class, "description")]/text()').get(),
                'source_url': exact_url,
                'status': parse_lead_status(raw_status_text or item_html),
                'posted_at': parse_posted_date(posted_text or item_html),
                'work_setup': parse_work_setup(raw_work_setup), 
                'location': raw_location.strip() or None,
            }

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super(ClientXpathSpider, cls).from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider.spider_closed, signal=signals.spider_closed)
        return spider

    async def spider_closed(self, spider):
        @sync_to_async
        def update_db():

            TargetSite.objects.filter(is_active=True).update(
                last_scraped=timezone.now(), 
                status='SUCCESS'
            )
        await update_db()
