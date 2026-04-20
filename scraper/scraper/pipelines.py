import logging
from leads.models import Lead
from textblob import TextBlob
from django.db import transaction
from django.core.exceptions import ValidationError
from django.db import connections

logger = logging.getLogger(__name__)

class DjangoLeadPipeline:
    def process_item(self, item, spider):
        try:
            site_id = item.get('site_id') 
            
            # Clean Data & Analyze Sentiment
            text = item.get('comment') or ''
            analysis = TextBlob(text)
            sentiment = analysis.sentiment.polarity

            # 2. Extract Data
            email = item.get('email')
            name = item.get('name') or "Unknown Client"
            job_title = item.get('job_title') or "Unknown Job Title"
            source_url = item.get('source_url')

            if not source_url:
                logger.warning(f"Skipping lead '{name}': Missing source_url")
                return item

            lead_data = {
                'site_id': site_id,
                'job_title': job_title,
                'sentiment_score': sentiment,
                'comment': text,
                'source_url': source_url,
                'status': item.get('status', 'UNKNOWN'),
                'posted_at': item.get('posted_at'),
                'work_setup': item.get('work_setup', 'UNKNOWN'),
                'location': item.get('location'),
            }

            with transaction.atomic():
                if not email:
                    lead, created = Lead.objects.get_or_create(
                        name=name,
                        source_url=source_url,
                        site_id=site_id,
                        defaults={**lead_data, 'email': None}
                    )
                    action = "created" if created else "already existed"
                else:
                    lead, created = Lead.objects.update_or_create(
                        email=email,
                        defaults={**lead_data, 'name': name}
                    )
                    action = "created" if created else "updated"

                logger.info(f"Lead '{name}' ({action})")

            return item

        except ValidationError as e:
            logger.error(f"Validation error: {e}")
            return item
        except Exception as e:
            logger.error(f"Database error: {str(e)}", exc_info=True)
            return item
        finally:
            for conn in connections.all():
                conn.close()
