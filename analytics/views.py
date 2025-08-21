import json
from datetime import timedelta
from django.db.models import Count
from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from .models import Visit, Event

def dashboard(request):
    return render(request, "analytics/dashboard.html")

def _base_qs():
    return Visit.objects.filter(is_bot=False)

def api_timeseries(request):
    days = int(request.GET.get("days", 30))
    end = timezone.now().date()
    start = end - timedelta(days=days - 1)

    qs = _base_qs().filter(ts__date__range=(start, end))

    pv = (
        qs.values("ts__date")
        .annotate(count=Count("id"))
        .order_by("ts__date")
    )

    uv = (
        qs.values("ts__date", "visitor_id").distinct()
        .values("ts__date")
        .annotate(count=Count("visitor_id"))
        .order_by("ts__date")
    )

    dates = [start + timedelta(days=i) for i in range(days)]
    pv_map = {row["ts__date"]: row["count"] for row in pv}
    uv_map = {row["ts__date"]: row["count"] for row in uv}

    data = {
        "labels": [d.strftime("%Y-%m-%d") for d in dates],
        "pageviews": [pv_map.get(d, 0) for d in dates],
        "visitors": [uv_map.get(d, 0) for d in dates],
    }
    return JsonResponse(data)

def api_top_pages(request):
    limit = int(request.GET.get("limit", 10))
    rows = (
        _base_qs()
        .values("path")
        .annotate(count=Count("id"))
        .order_by("-count")[:limit]
    )
    return JsonResponse({"rows": list(rows)})

def api_top_referrers(request):
    limit = int(request.GET.get("limit", 10))
    rows = (
        _base_qs()
        .exclude(referer="")
        .values("referer")
        .annotate(count=Count("id"))
        .order_by("-count")[:limit]
    )
    return JsonResponse({"rows": list(rows)})

def api_devices(request):
    qs = _base_qs()
    total = qs.count() or 1

    def bucket(q):
        return (
            q.filter(ua__iregex=r"mobile|iphone|android").count(),
            q.filter(ua__iregex=r"ipad|tablet").count(),
            q.filter(ua__iregex=r"windows|macintosh|linux").count(),
        )

    mobile, tablet, desktop = bucket(qs)
    return JsonResponse({
        "labels": ["Mobile", "Tablet", "Desktop"],
        "values": [mobile, tablet, desktop],
        "total": total,
    })

def api_os(request):
    """OS share by naive UA regex."""
    qs = _base_qs()
    def c(rx): return qs.filter(ua__iregex=rx).count()
    android = c(r"android")
    ios = c(r"iphone|ipad|ipod|ios")
    windows = c(r"windows nt")
    macos = c(r"macintosh|mac os x")
    linux = c(r"linux(?!.*android)")
    other = max(qs.count() - (android+ios+windows+macos+linux), 0)
    return JsonResponse({
        "labels": ["Android", "iOS", "Windows", "macOS", "Linux", "Other"],
        "values": [android, ios, windows, macos, linux, other],
    })

def api_browsers(request):
    """Browser share by naive UA regex."""
    qs = _base_qs()
    def c(rx): return qs.filter(ua__iregex=rx).count()
    chrome = c(r"chrome|crios|chromium") - c(r"edg/")  # avoid double-counting Edge
    safari = c(r"safari") - c(r"chrome|chromium|crios") # pure Safari
    edge = c(r"edg/")
    firefox = c(r"firefox")
    opera = c(r"opera|opr/")
    other = max(qs.count() - (chrome+safari+edge+firefox+opera), 0)
    return JsonResponse({
        "labels": ["Chrome", "Safari", "Edge", "Firefox", "Opera", "Other"],
        "values": [chrome, safari, edge, firefox, opera, other],
    })

def api_geo_countries(request):
    """Top countries (needs ANALYTICS_GEOIP=True + DB present)."""
    limit = int(request.GET.get("limit", 12))
    rows = (_base_qs()
            .exclude(country="")
            .values("country", "country_name")
            .annotate(count=Count("id"))
            .order_by("-count")[:limit])
    return JsonResponse({"rows": list(rows)})

def api_geo_cities(request):
    """Top cities within the last N days (optional)."""
    limit = int(request.GET.get("limit", 12))
    days = int(request.GET.get("days", 30))
    end = timezone.now()
    start = end - timedelta(days=days)
    rows = (_base_qs()
            .filter(ts__range=(start, end))
            .exclude(city="")
            .values("country", "city")
            .annotate(count=Count("id"))
            .order_by("-count")[:limit])
    return JsonResponse({"rows": list(rows)})

_geo_reader = None
def _geo_reader_get():
    global _geo_reader
    if _geo_reader is None and getattr(settings, "ANALYTICS_GEOIP", False):
        try:
            from geoip2.database import Reader
            _geo_reader = Reader(str(settings.ANALYTICS_GEOIP_DB_PATH))
        except Exception:
            _geo_reader = False
    return _geo_reader

def _geo_lookup(ip: str):
    r = _geo_reader_get()
    if not ip or not r:
        return ("", "", "")
    try:
        data = r.city(ip)
        return (data.country.iso_code or "", data.country.name or "", data.city.name or "")
    except Exception:
        return ("", "", "")

@csrf_exempt
def event_collect(request):
    if request.method != "POST":
        return HttpResponseBadRequest("POST only")
    try:
        payload = json.loads(request.body or "{}")
    except Exception:
        payload = {}

    evt = (payload.get("event") or "").strip().lower()
    if not evt:
        return HttpResponseBadRequest("Missing event")

    slug  = (payload.get("slug") or "")[:160]
    title = (payload.get("title") or "")[:256]

    ua = request.META.get("HTTP_USER_AGENT", "")[:500]
    ip = (request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip()
          or request.META.get("REMOTE_ADDR"))
    store_ip = getattr(settings, "ANALYTICS_STORE_IP", False)
    ip_to_save = ip if store_ip else None
    ip_hash = (ip and __import__("hashlib").sha256(ip.encode()).hexdigest()[:32]) or ""

    country, country_name, city = _geo_lookup(ip)

    visitor_id = request.COOKIES.get("v_id", "")
    session_key = getattr(getattr(request, "session", None), "session_key", "") or ""

    Event.objects.create(
        event=evt, slug=slug, title=title, path=request.META.get("PATH_INFO", ""),
        ua=ua, ip=ip_to_save, ip_hash=ip_hash,
        session_key=session_key, visitor_id=visitor_id,
        user=(getattr(request, "user", None) and request.user.is_authenticated) and request.user or None,
        country=country, country_name=country_name, city=city,
    )
    return HttpResponse(status=204)

def api_top_sermons(request):
    """Most played sermons by event='play'."""
    limit = int(request.GET.get("limit", 5))
    rows = (Event.objects.filter(event="play")
            .values("slug", "title")
            .annotate(count=Count("id"))
            .order_by("-count")[:limit])
    return JsonResponse({"rows": list(rows)})
