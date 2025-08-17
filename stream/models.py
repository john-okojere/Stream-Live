from django.db import models, transaction, IntegrityError
from django.utils.text import slugify
from django.urls import reverse
from datetime import datetime
from mutagen import File as MutagenFile

def cover_upload_to(instance, filename):
    return f"covers/{instance.date.strftime('%Y/%m')}/{filename}"

def audio_upload_to(instance, filename):
    return f"audio/{instance.date.strftime('%Y/%m')}/{filename}"

class Sermon(models.Model):
    title       = models.CharField(max_length=200)
    slug        = models.SlugField(max_length=220, unique=True, blank=True)
    speaker     = models.CharField(max_length=120, blank=True)
    date        = models.DateField(default=datetime.today)
    description = models.TextField(blank=True)
    tags        = models.CharField(max_length=200, blank=True, help_text="Comma-separated")
    cover       = models.ImageField(upload_to=cover_upload_to, blank=True, null=True)
    audio       = models.FileField(upload_to=audio_upload_to)
    duration_s  = models.PositiveIntegerField(default=0, help_text="Duration in seconds")

    class Meta:
        ordering = ["-date", "-id"]

    def save(self, *args, **kwargs):
        # Prepare a base slug if missing
        if not self.slug:
            base = self._base_slug()
            # keep room for suffixes like -123 (reserve up to 4 chars)
            self.slug = base[:136]

        # Try saving; on collision, append/increment a suffix and retry
        base = self._base_slug()
        max_len = 140
        attempt = 1
        while True:
            try:
                with transaction.atomic():
                    return super().save(*args, **kwargs)
            except IntegrityError:
                attempt += 1
                suffix = f"-{attempt}"
                # rebuild from base each time (avoids doubling suffixes)
                trimmed = base[: max_len - len(suffix)]
                self.slug = f"{trimmed}{suffix}"
                if attempt > 50:  # sanity cap
                    raise

    def _base_slug(self):
        return slugify(self.title) or "sermon"

    def duration_hm(self):
        m, s = divmod(self.duration_s or 0, 60)
        h, m = divmod(m, 60)
        return f"{h:d}:{m:02d}:{s:02d}" if h else f"{m:d}:{s:02d}"
    
    def tags_list(self):
        return [t.strip() for t in (self.tags or "").split(",") if t.strip()]

    def get_absolute_url(self):
        return reverse("stream:past_detail", args=[self.slug])

    def __str__(self):
        return f"{self.title} ({self.date})"
