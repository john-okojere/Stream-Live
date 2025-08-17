from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .models import Sermon
from .forms import SermonForm

def live(request):
    # Live page (your exact design, in template)
    return render(request, "stream/live.html")

def past_list(request):
    sermons = Sermon.objects.all()
    return render(request, "stream/past_list.html", {"sermons": sermons})

# views.py
from django.shortcuts import get_object_or_404, render
from .models import Sermon

def past_detail(request, slug):
    sermon = get_object_or_404(Sermon, slug=slug)
    # TODO: replace this with your real recommendation logic
    recs = Sermon.objects.exclude(pk=sermon.pk).order_by('-date')[:6]
    return render(request, "stream/past_detail.html", {
        "sermon": sermon,
        "recs": recs,
    })


@login_required
@user_passes_test(lambda u: u.is_staff)
def upload_sermon(request):
    if request.method == "POST":
        form = SermonForm(request.POST, request.FILES)
        if form.is_valid():
            sermon = form.save()
            messages.success(request, "Sermon uploaded.")
            return redirect(sermon.get_absolute_url())
    else:
        form = SermonForm()
    return render(request, "stream/upload.html", {"form": form})
