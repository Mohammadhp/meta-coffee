import subprocess
import sys

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand

BASE_DIR = settings.BASE_DIR


class Command(BaseCommand):
    help = "Scrape all sources and import the catalog. One-shot refresh (cron)."

    def handle(self, *args, **opts):
        self.stdout.write(">> scraping sources ...")
        proc = subprocess.run(
            [sys.executable, str(BASE_DIR / "scraper" / "scrape.py")],
            cwd=BASE_DIR,
        )
        if proc.returncode != 0:
            self.stderr.write(self.style.ERROR(
                "scraper exited with a non-zero status; keeping the previous catalog."
            ))
            raise SystemExit(proc.returncode)
        self.stdout.write(">> importing catalog ...")
        call_command("import_catalog", stdout=self.stdout, stderr=self.stderr)
