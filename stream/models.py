# stream/models.py
from django.db import models, transaction, IntegrityError
from django.urls import reverse
from django.utils.text import slugify
from django.utils import timezone
from django.conf import settings
from tempfile import NamedTemporaryFile
from mutagen import File as MutagenFile
import shutil
import os

def cover_upload_to(instance, filename):
    d = getattr(instance, "date", None) or timezone.localdate()
    return f"covers/{d.strftime('%Y/%m')}/{filename}"

def audio_upload_to(instance, filename):
    d = getattr(instance, "date", None) or timezone.localdate()
    return f"audio/{d.strftime('%Y/%m')}/{filename}"

class Sermon(models.Model):
    title       = models.CharField(max_length=200, db_index=True)
    slug        = models.SlugField(max_length=220, unique=True, blank=True)
    speaker     = models.CharField(max_length=120, blank=True, db_index=True)
    date        = models.DateField(default=timezone.localdate, db_index=True)
    description = models.TextField(blank=True)
    tags        = models.CharField(max_length=200, blank=True, help_text="Comma-separated")
    cover       = models.ImageField(upload_to=cover_upload_to, blank=True, null=True)
    audio       = models.FileField(upload_to=audio_upload_to)
    duration_s  = models.PositiveIntegerField(default=0, help_text="Duration in seconds")

    class Meta:
        ordering = ["-date", "-id"]

    def __str__(self):
        return f"{self.title} ({self.date})"

    def _base_slug(self) -> str:
        return slugify(self.title) or "sermon"

    def _trim_slug_to_field(self, base: str, suffix_len: int = 0) -> str:
        max_len = self._meta.get_field("slug").max_length
        return base[: max_len - suffix_len]

    def duration_hm(self) -> str:
        m, s = divmod(self.duration_s or 0, 60)
        h, m = divmod(m, 60)
        return f"{h:d}:{m:02d}:{s:02d}" if h else f"{m:d}:{s:02d}"

    def tags_list(self):
        return [t.strip() for t in (self.tags or "").split(",") if t.strip()]

    def get_absolute_url(self):
        return reverse("stream:past_detail", args=[self.slug])

    def save(self, *args, **kwargs):
        # set initial slug if missing
        if not self.slug:
            self.slug = self._trim_slug_to_field(self._base_slug())

        # unique slug collision handling
        base = self._base_slug()
        attempt = 1
        while True:
            try:
                with transaction.atomic():
                    super().save(*args, **kwargs)
                break
            except IntegrityError:
                attempt += 1
                if attempt > 50:
                    raise
                suffix = f"-{attempt}"
                self.slug = self._trim_slug_to_field(base, suffix_len=len(suffix)) + suffix

        # probe duration once the file exists
        if self.audio and (self.duration_s or 0) == 0:
            dur = self._probe_audio_duration()
            if dur:
                self.duration_s = dur
                super().save(update_fields=["duration_s"])

    def _probe_audio_duration(self) -> int | None:
        try:
            if hasattr(self.audio, "path") and os.path.exists(self.audio.path):
                audio = MutagenFile(self.audio.path)
                return int(audio.info.length) if audio and audio.info else None
            with self.audio.open("rb") as src, NamedTemporaryFile(suffix=os.path.splitext(self.audio.name)[1]) as tmp:
                shutil.copyfileobj(src, tmp)
                tmp.flush()
                audio = MutagenFile(tmp.name)
                return int(audio.info.length) if audio and audio.info else None
        except Exception:
            return None

# ======= Spotify-like models =======

class Playlist(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                              on_delete=models.SET_NULL, related_name="playlists")
    title = models.CharField(max_length=160)
    slug  = models.SlugField(max_length=180, unique=True)
    is_public = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["slug"])]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title) or "playlist"
            self.slug = base[:170]
        return super().save(*args, **kwargs)

class PlaylistItem(models.Model):
    playlist = models.ForeignKey(Playlist, related_name="items", on_delete=models.CASCADE)
    sermon   = models.ForeignKey(Sermon, on_delete=models.CASCADE)
    position = models.PositiveIntegerField()

    class Meta:
        ordering = ["position"]
        unique_together = (("playlist", "position"),)
        indexes = [models.Index(fields=["playlist", "position"])]

class Library(models.Model):
    user   = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="library")
    sermon = models.ForeignKey(Sermon, on_delete=models.CASCADE)
    saved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (("user", "sermon"),)
        indexes = [models.Index(fields=["user", "sermon"])]

class PlayEvent(models.Model):
    user        = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    sermon      = models.ForeignKey(Sermon, on_delete=models.CASCADE)
    started_at  = models.DateTimeField(auto_now_add=True)
    progress_s  = models.FloatField(default=0)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["sermon", "started_at"])]
