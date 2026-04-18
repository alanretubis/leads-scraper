import scrapy
import urllib.parse
from scrapy import signals
from django.utils import timezone
from asgiref.sync import sync_to_async
from leads.models import TargetSite
import re

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

            email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
            found_emails = re.findall(email_pattern, item_html)
            email = found_emails[0] if found_emails else item.xpath('.//a[contains(@href, "mailto:")]/@href').re_first(r'mailto:([^?]+)')
        
            raw_name = item.xpath('.//small[@class="author"]/text() | .//h3/a/@title | .//h4/text() | .//h3/text() | .//a[contains(@class, "title")]/text()').get()
            
            yield {
                'site_id': target_id,
                'name': company_name.strip() if company_name else "Unknown Company",
                'job_title': job_title.strip() if job_title else "Unknown Position",
                'email': email,
                'comment': item.xpath('.//span[@class="text"]/text() | .//div[contains(@class, "description")]/text()').get(),
                'source_url': exact_url,
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
