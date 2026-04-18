from django.contrib import admin, messages
from django.urls import path
from django.utils.html import format_html 
from .models import Lead, TargetSite
import os
import subprocess
from django.http import HttpResponseRedirect

@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):

    list_display = ('job_title', 'name', 'email', 'site', 'created_at', 'source_url')
    search_fields = ('job_title', 'name', 'email')
    list_filter = ('job_title', 'site', 'created_at')
    ordering = ('job_title',)


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

    def view_source_url(self, obj):
        if obj.source_url:
            return format_html(
                '<a href="{}" target="_blank" rel="noopener noreferrer">{}</a>',
                obj.source_url,
                obj.source_url
            )
        return "-"

    view_source_url.short_description = 'Source URL'

@admin.register(TargetSite)
class TargetSiteAdmin(admin.ModelAdmin):
    list_display = ('site_name', 'url_template', 'keywords', 'status', 'last_scraped', 'category', 'is_active')
    list_filter = ('status', 'category')
    readonly_fields = ('last_scraped', 'status')
