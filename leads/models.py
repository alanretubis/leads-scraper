from django.db import models

class TargetSite(models.Model):
    site_name = models.CharField(max_length=100)
    base_url = models.URLField(unique=True)
    url_template = models.CharField(max_length=500, default='https://placeholder.com{keyword}') 
    keywords = models.CharField(max_length=255, blank=True, help_text="Keywords separated by commas") 
    category = models.CharField(max_length=50) # e.g., 'E-commerce', 'Professional'
    is_active = models.BooleanField(default=True)
    last_scraped = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20, 
        choices=[('PENDING', 'Pending'), ('SUCCESS', 'Success'), ('FAILED', 'Failed')],
        default='PENDING'
    )

    def __str__(self):
        return f"{self.site_name}"
    
class Lead(models.Model):
    site = models.ForeignKey(
        TargetSite, 
        on_delete=models.CASCADE, 
        related_name='leads',
        null=True, 
        blank=True
    )
    name = models.CharField(max_length=255, null=True, blank=True) 
    email = models.EmailField(unique=True, null=True, blank=True)
    job_title = models.CharField(max_length=255, null=True, blank=True) 
    source_url = models.URLField()
    sentiment_score = models.FloatField(default=0.0) # -1.0 to 1.0
    work_setup = models.TextField(null=True, blank=True)
    location = models.TextField(null=True, blank=True)
    comment = models.TextField(null=True, blank=True)
    posted_at = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ('OPEN', 'Open / Hiring'),
            ('CLOSED', 'Closed / Not Hiring'),
            ('UNKNOWN', 'Unknown'),
        ],
        default='UNKNOWN'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['email'],
                condition=models.Q(email__isnull=False),
                name='unique_email_when_not_null'
            )
        ]

    def __str__(self):
        return f"{self.name}"
