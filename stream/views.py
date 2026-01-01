from datetime import timedelta
from collections import Counter

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Count, Q
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateformat import format as datefmt
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import DetailView, ListView

from analytics.models import Event, Visit

from .forms import SermonForm
from .models import Sermon


def live(request):
    # Live page (your exact design, in template)
    return render(request, "stream/live.html")

@login_required
@user_passes_test(lambda u: u.is_staff)
def upload_sermon(request):
    if request.method == "POST":
        form = SermonForm(request.POST, request.FILES)
        if form.is_valid():
            sermon = form.save(commit=False)
            sermon.uploaded_by = request.user
            sermon.save()
            messages.success(request, "Sermon uploaded.")
            return redirect(sermon.get_absolute_url())
    else:
        form = SermonForm()
    return render(request, "stream/upload.html", {"form": form})


@login_required
@user_passes_test(lambda u: u.is_staff)
def staff_dashboard(request):
    now = timezone.now()
    since = now - timedelta(days=7)

    sermons_total = Sermon.objects.count()
    sermons_week = Sermon.objects.filter(date__gte=since.date()).count()
    plays_week = Event.objects.filter(event="play", ts__gte=since).count()
    visits_week = Visit.objects.filter(ts__gte=since).count()

    top_sermons = (
        Event.objects.filter(event="play")
        .values("slug", "title")
        .annotate(count=Count("id"))
        .order_by("-count")[:5]
    )
    recent_sermons = Sermon.objects.order_by("-date", "-id")[:6]
    recent_events = Event.objects.filter(event="play").order_by("-ts")[:8]
    recent_visits = Visit.objects.order_by("-ts")[:8]

    context = {
        "sermons_total": sermons_total,
        "sermons_week": sermons_week,
        "plays_week": plays_week,
        "visits_week": visits_week,
        "top_sermons": top_sermons,
        "recent_sermons": recent_sermons,
        "recent_events": recent_events,
        "recent_visits": recent_visits,
    }
    return render(request, "stream/staff_dashboard.html", context)



class SermonListView(ListView):
    template_name = "stream/past_list.html"
    context_object_name = "object_list"
    paginate_by = 12

    def get_queryset(self):
        qs = (
            Sermon.objects.all()
            .only("id", "slug", "title", "speaker", "date", "duration_s", "tags", "cover", "audio")
            .order_by("-date", "-id")
        )

        q = (self.request.GET.get("q") or "").strip()
        tag = (self.request.GET.get("tag") or "").strip().lstrip("#")
        year = (self.request.GET.get("year") or "").strip()
        speaker = (self.request.GET.get("speaker") or "").strip()

        # Tokenized AND-style search across fields
        if q:
            tokens = [t for t in q.replace("#", " ").split() if t]
            for t in tokens:
                qs = qs.filter(
                    Q(title__icontains=t)
                    | Q(speaker__icontains=t)
                    | Q(tags__icontains=t)
                    | Q(description__icontains=t)
                )

        if tag:
            qs = qs.filter(tags__icontains=tag)

        if year.isdigit():
            qs = qs.filter(date__year=int(year))

        if speaker:
            qs = qs.filter(speaker__icontains=speaker)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        # Active filters for UI
        ctx["q"] = self.request.GET.get("q", "")
        ctx["active_tag"] = self.request.GET.get("tag", "")
        ctx["active_year"] = self.request.GET.get("year", "")
        ctx["active_speaker"] = self.request.GET.get("speaker", "")

        # Years for sidebar
        years = Sermon.objects.dates("date", "year", order="DESC")
        ctx["years"] = [d.year for d in years]

        # Top tags (simple Python counter over comma-separated tags)
        tag_counter = Counter()
        for row in Sermon.objects.values_list("tags", flat=True):
            if not row:
                continue
            for t in [s.strip() for s in row.split(",") if s.strip()]:
                tag_counter[t.lower()] += 1
        ctx["top_tags"] = sorted(tag_counter.items(), key=lambda x: (-x[1], x[0]))[:12]

        # Top speakers
        ctx["top_speakers"] = (
            Sermon.objects.values("speaker")
            .exclude(speaker="")
            .annotate(n=Count("id"))
            .order_by("-n", "speaker")[:12]
        )
        return ctx


class SermonDetailView(DetailView):
    model = Sermon
    template_name = "stream/past_detail.html"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        s = self.object

        # Related by same speaker or overlapping tags; fallback to newest
        rel = Sermon.objects.exclude(id=s.id)
        if s.speaker:
            rel = rel.filter(Q(speaker__iexact=s.speaker) | Q(tags__icontains=s.speaker))
        if s.tags:
            for t in [x.strip() for x in s.tags.split(",") if x.strip()]:
                rel = rel | Sermon.objects.exclude(id=s.id).filter(tags__icontains=t)
        ctx["related"] = rel.order_by("-date", "-id").distinct()[:6]
        return ctx


# JSON for Details Modal / Global Player
def sermon_json(request, slug):
    try:
        s = Sermon.objects.get(slug=slug)
    except Sermon.DoesNotExist:
        raise Http404
    return JsonResponse(
        {
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
        }
    )


# Optional: accept progress beacons from player.js without CSRF errors
@csrf_exempt
def progress_ping(request):
    if request.method not in ("POST", "OPTIONS"):
        return HttpResponse(status=405)
    # TODO: persist progress if you have user sessions / a model
    return HttpResponse(status=204)

from django.utils.dateformat import format as datefmt
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse

def sermons_list_json(request):
    """Return paginated sermons for SPA filtering/search without navigating."""
    q = (request.GET.get("q") or "").strip()
    tag = (request.GET.get("tag") or "").strip().lstrip("#")
    year = (request.GET.get("year") or "").strip()
    speaker = (request.GET.get("speaker") or "").strip()
    page = int(request.GET.get("page", 1))

    qs = (
        Sermon.objects.all()
        .only("id", "slug", "title", "speaker", "date", "duration_s", "tags", "cover", "audio")
        .order_by("-date", "-id")
    )

    # Tokenized AND-style search
    if q:
        tokens = [t for t in q.replace("#", " ").split() if t]
        for t in tokens:
            qs = qs.filter(
                Q(title__icontains=t)
                | Q(speaker__icontains=t)
                | Q(tags__icontains=t)
                | Q(description__icontains=t)
            )

    if tag:
        qs = qs.filter(tags__icontains=tag)
    if year.isdigit():
        qs = qs.filter(date__year=int(year))
    if speaker:
        qs = qs.filter(speaker__icontains=speaker)

    paginator = Paginator(qs, 12)
    page_obj = paginator.get_page(page)

    items = []
    for s in page_obj:
        items.append({
            "slug": s.slug,
            "title": s.title,
            "speaker": s.speaker,
            "date_display": datefmt(s.date, "M j, Y"),  # ← portable (e.g., "Aug 21, 2025")
            "duration_hm": s.duration_hm(),
            "tags": s.tags_list(),
            "cover": s.cover.url if s.cover else "",
            "absolute_url": request.build_absolute_uri(s.get_absolute_url()),
        })


    return JsonResponse({
        "items": items,
        "page": page_obj.number,
        "pages": paginator.num_pages,
        "has_next": page_obj.has_next(),
        "has_prev": page_obj.has_previous(),
        "q": q, "tag": tag, "year": year, "speaker": speaker,
    })

from collections import Counter
from random import sample
from django.http import JsonResponse
from django.utils.dateformat import format as datefmt

from .models import Sermon

def sidebar_summary_json(request):
    """
    Returns:
      - top_tags: most used overall (name, count)
      - recent_tags: most used in latest N items
      - random_items: 3 random picks from last ~100 (slug/title/speaker/date/duration/cover)
    """
    # Top tags (all-time)
    tag_counter = Counter()
    for row in Sermon.objects.values_list("tags", flat=True):
        if not row:
            continue
        for t in [x.strip() for x in row.split(",") if x.strip()]:
            tag_counter[t.lower()] += 1
    top_tags = [{"name": k, "count": v} for k, v in tag_counter.most_common(18)]

    # Recent tags (from latest 40)
    recent_counter = Counter()
    for s in Sermon.objects.only("tags").order_by("-date", "-id")[:40]:
        if not s.tags:
            continue
        for t in [x.strip() for x in s.tags.split(",") if x.strip()]:
            recent_counter[t.lower()] += 1
    recent_tags = [{"name": k, "count": v} for k, v in recent_counter.most_common(18)]

    # Random 3 from latest 100 (fast/consistent)
    pool = list(
        Sermon.objects.only("slug", "title", "speaker", "date", "duration_s", "cover")
        .order_by("-date", "-id")[:100]
    )
    picks = sample(pool, k=min(5, len(pool)))
    random_items = []
    for s in picks:
        random_items.append({
            "slug": s.slug,
            "title": s.title[:15],
            "speaker": s.speaker[:15],
            "date_display": datefmt(s.date, "M j, Y"),
            "duration_hm": s.duration_hm(),
            "cover": s.cover.url if s.cover else "",
        })
    return JsonResponse({
        "top_tags": top_tags[:5],
        "recent_tags": recent_tags[:5],
        "random_items": random_items[:5],
    })

