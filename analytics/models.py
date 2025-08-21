from django.conf import settings
from django.db import models
from django.utils import timezone

class Visit(models.Model):
    ts = models.DateTimeField(default=timezone.now, db_index=True)
    session_key = models.CharField(max_length=40, db_index=True)
    visitor_id = models.CharField(max_length=36, db_index=True)  # UUID cookie
    user = models.ForeignKey(
        getattr(settings, "AUTH_USER_MODEL", "auth.User"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    path = models.CharField(max_length=512, db_index=True)
    method = models.CharField(max_length=8)
    status_code = models.SmallIntegerField(null=True, blank=True, db_index=True)
    response_ms = models.IntegerField(null=True, blank=True)
    referer = models.URLField(max_length=1024, blank=True)
    ua = models.TextField(blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    ip_hash = models.CharField(max_length=64, blank=True)
    utm_source = models.CharField(max_length=64, blank=True)
    utm_medium = models.CharField(max_length=64, blank=True)
    utm_campaign = models.CharField(max_length=64, blank=True)
    utm_term = models.CharField(max_length=64, blank=True)
    utm_content = models.CharField(max_length=64, blank=True)
    is_bot = models.BooleanField(default=False, db_index=True)
    country = models.CharField(max_length=2, blank=True)        # ISO-2 (e.g., NG, US)
    country_name = models.CharField(max_length=64, blank=True)  # Nigeria, United States...
    city = models.CharField(max_length=64, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["ts"]),
            models.Index(fields=["path"]),
            models.Index(fields=["-ts", "path"]),
            models.Index(fields=["visitor_id", "ts"]),
        ]
        ordering = ["-ts"]

    def __str__(self):
        return f"{self.path} [{self.status_code}] @ {self.ts:%Y-%m-%d %H:%M:%S}"

# ... existing imports ...
from django.utils import timezone

class Event(models.Model):
    ts = models.DateTimeField(default=timezone.now, db_index=True)
    session_key = models.CharField(max_length=40, blank=True, db_index=True)
    visitor_id = models.CharField(max_length=36, blank=True, db_index=True)
    user = models.ForeignKey(getattr(settings, 'AUTH_USER_MODEL', 'auth.User'), null=True, blank=True, on_delete=models.SET_NULL)

    event = models.CharField(max_length=32, db_index=True)  # e.g., "play"
    slug = models.CharField(max_length=160, blank=True, db_index=True)
    title = models.CharField(max_length=256, blank=True)
    path = models.CharField(max_length=512, blank=True)

    ua = models.TextField(blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    ip_hash = models.CharField(max_length=64, blank=True)

    # optional geo (derived; no need to store raw IP)
    country = models.CharField(max_length=2, blank=True)
    country_name = models.CharField(max_length=64, blank=True)
    city = models.CharField(max_length=64, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['event', 'slug']),
            models.Index(fields=['-ts', 'event']),
        ]
        ordering = ['-ts']

    def __str__(self):
        return f"{self.event} • {self.slug or self.title} @ {self.ts:%Y-%m-%d %H:%M}"
