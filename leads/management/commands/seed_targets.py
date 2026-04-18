from django.core.management.base import BaseCommand
from leads.models import Lead, TargetSite

class Command(BaseCommand):
    help = 'Seeds the database with high-value job lead targets and broad tech keywords'

    def handle(self, *args, **kwargs):
        self.stdout.write("Cleaning database...")
        Lead.objects.all().delete()
        TargetSite.objects.all().delete()
        self.stdout.write(self.style.SUCCESS("Database cleared."))

        # Keywords
        core_dev = "Full-stack Developer, Software Developer, Software Engineer"
        frontend = "React Developer, Vue.js Developer, Frontend Engineer"
        backend = "Python Developer, Django Developer, Node.js Developer, Go Developer"
        mobile = "React Native Developer, Flutter Developer, iOS Developer"
        all_keywords = f"{core_dev}, {frontend}, {backend}, {mobile}"

        targets = [
            {
                'site_name': 'LinkedIn Jobs',
                'base_url': 'https://linkedin.com',
                # LinkedIn uses /jobs/search/?keywords=
                'url_template': 'https://www.linkedin.com/jobs/search?keywords={keyword}',
                'keywords': all_keywords,
                'category': 'Professional'
            },
            {
                'site_name': 'Indeed Philippines',
                'base_url': 'https://indeed.com',
                # Indeed uses /jobs?q=
                'url_template': 'https://www.indeed.com/jobs?q={keyword}',
                'keywords': all_keywords,
                'category': 'General Job Board'
            },
            {
                'site_name': 'OnlineJobs.ph',
                'base_url': 'https://onlinejobs.ph',
                # OnlineJobs uses /jobseekers/jobsearch?jobkeyword=
                'url_template': 'https://www.onlinejobs.ph/jobseekers/jobsearch?jobkeyword={keyword}',
                'keywords': all_keywords,
                'category': 'Freelance/Remote'
            },
            {
                'site_name': 'JobStreet PH',
                'base_url': 'https://jobstreet.com.ph',
                # JobStreet: uses /{keyword}-jobs
                'url_template': 'https://jobstreet.com.ph/{keyword}-jobs/',
                'keywords': all_keywords,
                'category': 'General Job Board'
            },
            {
                'site_name': 'We Work Remotely',
                'base_url': 'https://weworkremotely.com',
                # WWR uses /remote-jobs/search?term=
                'url_template': 'https://weworkremotely.com/remote-jobs/search?term={keyword}',
                'keywords': all_keywords,
                'category': 'Remote Tech'
            },
            {
                'site_name': 'Upwork',
                'base_url': 'https://upwork.com',
                # Upwork uses /nx/search/jobs/?q=
                'url_template': 'https://www.upwork.com/nx/search/jobs/?q={keyword}',
                'keywords': all_keywords,
                'category': 'Freelance'
            },
        ]

        for target in targets:
            obj, created = TargetSite.objects.update_or_create(
                site_name=target['site_name'],
                defaults=target
            )
            status = "Added" if created else "Updated"
            self.stdout.write(self.style.SUCCESS(f"{status}: {target['site_name']}"))
