# stream/api.py
from django.http import JsonResponse, HttpResponseForbidden, Http404
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateformat import format as datefmt
from .models import Sermon, Library, PlayEvent
from django.urls import reverse

def _sermon_dict(s: Sermon):
    return {
        "id": s.id,
        "slug": s.slug,
        "title": s.title,
        "speaker": s.speaker,
        "date": s.date.isoformat(),
        "duration_s": s.duration_s,
        "cover": s.cover.url if s.cover else "",
        "audio": s.audio.url,
    }

def sermon_json(request, slug):
    try:
        s = Sermon.objects.get(slug=slug)
    except Sermon.DoesNotExist:
        raise Http404
    return JsonResponse({
        "slug": s.slug,
        "title": s.title,
        "speaker": s.speaker,
        "cover": s.cover.url if s.cover else "",
        "audio": s.audio.url,
        "duration_s": s.duration_s or 0,
        "duration_hm": s.duration_hm(),
        "date_display": datefmt(s.date, "M j, Y"),
        "tags": s.tags_list(),
        "description": s.description or "",
        "absolute_url": request.build_absolute_uri(reverse("stream:past_detail", args=[s.slug])),
    })

@require_GET
def search_json(request):
    q = (request.GET.get("q") or "").strip()
    qs = Sermon.objects.all()
    if q:
        qs = qs.filter(title__icontains=q) | qs.filter(speaker__icontains=q) | qs.filter(tags__icontains=q)
    data = [_sermon_dict(s) for s in qs[:30]]
    return JsonResponse({"results": data})

@require_POST
def library_toggle(request):
    if not request.user.is_authenticated:
        return HttpResponseForbidden("Login required")
    slug = request.POST.get("slug")
    s = get_object_or_404(Sermon, slug=slug)
    obj, created = Library.objects.get_or_create(user=request.user, sermon=s)
    if not created:
        obj.delete()
        return JsonResponse({"saved": False})
    return JsonResponse({"saved": True})

@csrf_exempt  # allow beacon pings without CSRF
@require_POST
def progress_ping(request):
    slug = request.POST.get("slug")
    try:
        progress_s = float(request.POST.get("progress_s", "0") or 0)
    except ValueError:
        progress_s = 0.0
    s = get_object_or_404(Sermon, slug=slug)
    pe = PlayEvent.objects.create(
        user=request.user if request.user.is_authenticated else None,
        sermon=s,
        progress_s=progress_s,
    )
    if s.duration_s and progress_s >= 0.9 * s.duration_s and pe.completed_at is None:
        pe.completed_at = timezone.now()
        pe.save(update_fields=["completed_at"])
    return JsonResponse({"ok": True})
