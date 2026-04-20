from django.contrib import admin, messages
from django.urls import path
from django.utils.html import format_html 
from .models import Lead, TargetSite
import os
import subprocess
from django.http import HttpResponseRedirect

@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    autocomplete_fields = ['site']
    list_display = ('view_job_title', 'view_source_url', 'view_company_name', 'email', 'site', 'status', 'work_setup', 'location', 'posted_at', 'created_at')
    fields = ('site', 'job_title', 'name', 'email', 'status', 'work_setup', 'location', 'source_url', 'posted_at')
    search_fields = ('job_title', 'name', 'email')
    list_filter = ('status', 'posted_at', 'work_setup', 'site', 'created_at')
    ordering = ('job_title',)
    readonly_fields = ('site', 'posted_at', 'source_url')


    # 'Run Scrapers' Button
    change_list_template = "admin/leads/leads/scrape_button.html"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('run-scrapers/', self.admin_site.admin_view(self.run_scrapers_view), name='run-scrapers'),
        ]
        return custom_urls + urls

    def run_scrapers_view(self, request):
        try:
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            scraper_cwd = os.path.join(project_root, 'scraper')
            
            subprocess.Popen(
                ['scrapy', 'crawl', 'client_xpath_spider'],
                cwd=scraper_cwd
            )
            self.message_user(request, "Scraping started!", messages.SUCCESS)
        except Exception as e:
            self.message_user(request, f"Error: {str(e)}", messages.ERROR)
            
        return HttpResponseRedirect("../")

    def view_job_title(self, obj):
        title = obj.job_title or "Unknown Position"
        if len(title) > 25:
            # 'title' attribute creates the browser tooltip on hover
            return format_html('<span title="{}">{}...</span>', title, title[:25])
        return title
    
    view_job_title.short_description = 'Job Title'
    view_job_title.admin_order_field = 'job_title'

    def view_company_name(self, obj):
        name = obj.name or "Unknown Company"
        if len(name) > 25:
            return format_html('<span title="{}">{}...</span>', name, name[:25])
        return name
    view_company_name.short_description = 'Name'
    view_company_name.admin_order_field = 'name'
    
    def view_source_url(self, obj):
        return format_html('<a href="{0}" target="_blank">View</a>', obj.source_url) if obj.source_url else "-"

    view_source_url.short_description = 'URL'

@admin.register(TargetSite)
class TargetSiteAdmin(admin.ModelAdmin):
    search_fields = ('site_name',) 
    list_display = ('site_name', 'url_template', 'keywords', 'status', 'last_scraped', 'category', 'is_active')
    list_filter = ('status', 'category')
    readonly_fields = ('last_scraped', 'status')
