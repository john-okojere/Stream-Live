import re, time, uuid, hashlib
from django.utils import timezone
from django.conf import settings

BOT_REGEX = re.compile(
    r"bot|crawl|spider|slurp|bingpreview|crawler|facebookexternalhit|whatsapp|telegram|curl|python-requests|fetch|monitoring",
    re.I,
)
EXCLUDE_PATHS = ("/admin/", "/static/", "/media/", "/favicon.ico", "/robots.txt", "/health")

_geo_reader = None
def _get_geo_reader():
    global _geo_reader
    if _geo_reader is None and getattr(settings, "ANALYTICS_GEOIP", False):
        try:
            from geoip2.database import Reader
            _geo_reader = Reader(str(settings.ANALYTICS_GEOIP_DB_PATH))
        except Exception:
            _geo_reader = False
    return _geo_reader

def _geo_lookup(ip: str):
    """
    Returns (country_code, country_name, city) or ('', '', '') if unavailable.
    Called per request; reader is kept as a module singleton.
    """
    reader = _get_geo_reader()
    if not ip or not reader:
        return ("", "", "")
    try:
        r = reader.city(ip)
        return (r.country.iso_code or "", r.country.name or "", r.city.name or "")
    except Exception:
        return ("", "", "")

class VisitMiddleware:
    """Log each request. Place AFTER session & auth middleware."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if any(request.path.startswith(p) for p in EXCLUDE_PATHS):
            return self.get_response(request)

        start = time.perf_counter()

        # ensure session key
        if not getattr(request, "session", None) or not request.session.session_key:
            try:
                request.session["__touch__"] = True
                request.session.save()
            except Exception:
                pass

        visitor_id = request.COOKIES.get("v_id") or str(uuid.uuid4())
        set_cookie = "v_id" not in request.COOKIES

        response = self.get_response(request)

        try:
            from .models import Visit
            ua = request.META.get("HTTP_USER_AGENT", "")[:500]
            is_bot = bool(BOT_REGEX.search(ua))
            ip = (request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip()
                  or request.META.get("REMOTE_ADDR"))

            # Privacy: do NOT store raw IP unless enabled
            store_ip = getattr(settings, "ANALYTICS_STORE_IP", False)
            ip_to_save = ip if store_ip else None
            ip_hash = hashlib.sha256((ip or "").encode()).hexdigest()[:32] if ip else ""

            # Geo derivation (we store only derived fields)
            country, country_name, city = _geo_lookup(ip)

            utm = {k: request.GET.get(k, "") for k in ("utm_source","utm_medium","utm_campaign","utm_term","utm_content")}
            dur_ms = int((time.perf_counter() - start) * 1000)

            Visit.objects.create(
                ts=timezone.now(),
                session_key=(getattr(request, "session", None) and request.session.session_key) or "",
                visitor_id=visitor_id,
                user=(getattr(request, "user", None) and request.user.is_authenticated) and request.user or None,
                path=request.path,
                method=request.method,
                status_code=getattr(response, "status_code", None),
                response_ms=dur_ms,
                referer=request.META.get("HTTP_REFERER", "")[:1024],
                ua=ua,
                ip=ip_to_save,
                ip_hash=ip_hash,
                is_bot=is_bot,
                country=country,
                country_name=country_name,
                city=city,
                **utm,
            )
        except Exception:
            pass

        if set_cookie:
            try:
                response.set_cookie(
                    "v_id", visitor_id,
                    max_age=60*60*24*365*2, httponly=True, samesite="Lax", secure=True
                )
            except Exception:
                pass
        return response
