from django.db import models
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
        # slug
        if not self.slug:
            base = slugify(self.title) or slugify(self.date.isoformat())
            slug = base
            i = 2
            while Sermon.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{i}"
                i += 1
            self.slug = slug

        # duration (best effort)
        if self.audio and (not self.duration_s or self.duration_s == 0):
            try:
                mf = MutagenFile(self.audio)
                if mf and mf.info and mf.info.length:
                    self.duration_s = int(mf.info.length)
            except Exception:
                pass

        super().save(*args, **kwargs)

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
