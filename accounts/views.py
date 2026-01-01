# accounts/views.py
from __future__ import annotations
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import Group
from django.contrib.auth.views import (
    PasswordChangeView, PasswordChangeDoneView,
    PasswordResetView, PasswordResetDoneView,
    PasswordResetConfirmView, PasswordResetCompleteView,
)
from django.shortcuts import redirect, render, get_object_or_404
from django.db.models import Q
from django.urls import reverse_lazy
from .forms import (
    RegisterForm, EmailAuthenticationForm,
    UserCreateWithRolesForm, UserEditForm, UserSetPasswordForm,
)
from .models import User

def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = EmailAuthenticationForm(request=request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.get_user()
        login(request, user)
        messages.success(request, f"Welcome back, {user.first_name or user.email}!")
        return redirect(request.GET.get("next") or "dashboard")
    return render(request, "accounts/login.html", {"form": form})

def register_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save(commit=False)
        # ensure active; add any business logic here
        user.is_active = True
        user.save()
        messages.success(request, "Account created. You can now sign in.")
        return redirect("login")
    return render(request, "accounts/register.html", {"form": form})

def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect("login")


def profile_view(request, uid):
    user = get_object_or_404(User, uid=uid)
    return render(request, "profiles/profile.html", {"profile_user": user})


# ---- Users management (Admin-only) ----

def _is_admin(user):
    return user.is_authenticated and user.groups.filter(name="Admin").exists()


def _can_edit_users(user):
    # Admin or users with change_user (e.g., IT Support for password resets)
    return user.is_authenticated and (user.has_perm("accounts.change_user") or _is_admin(user))


def admin_required(view):
    return login_required(user_passes_test(lambda u: _is_admin(u))(view))


def manage_required(view):
    return login_required(user_passes_test(lambda u: _can_edit_users(u))(view))


@admin_required
def users_list(request):
    q = (request.GET.get("q") or "").strip()
    qs = User.objects.all().order_by("-date_joined")
    if q:
        qs = qs.filter(
            Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(email__icontains=q)
        )
    users = qs[:200]
    role_names = ["Admin", "IT Support", "Socials", "Followup Supervisors", "Followup Agents"]
    return render(request, "accounts/user_list.html", {"users": users, "q": q, "role_names": role_names})


@admin_required
def user_create(request):
    if request.method == "POST":
        form = UserCreateWithRolesForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = form.cleaned_data.get("is_active")
            user.save()
            groups = form.cleaned_data.get("groups")
            if groups is not None:
                user.groups.set(groups)
            messages.success(request, "User created.")
            return redirect("user_list")
    else:
        form = UserCreateWithRolesForm()
    return render(request, "accounts/user_form.html", {"form": form, "create": True})


@manage_required
def user_edit(request, uid):
    user = get_object_or_404(User, uid=uid)
    is_admin = _is_admin(request.user)
    pwd_form = None
    if request.method == "POST":
        if request.POST.get("action") == "set_password":
            pwd_form = UserSetPasswordForm(user, request.POST)
            form = UserEditForm(request.POST, instance=user)
            if pwd_form.is_valid():
                pwd_form.save()
                messages.success(request, "Password updated.")
                return redirect("user_edit", uid=user.uid)
        else:
            # Only Admins can change profile/roles; others ignore
            if not is_admin:
                messages.error(request, "You are not allowed to edit user details.")
                return redirect("user_edit", uid=user.uid)
            form = UserEditForm(request.POST, instance=user)
            if form.is_valid():
                u = form.save()
                messages.success(request, "User updated.")
                return redirect("user_edit", uid=u.uid)
    else:
        form = UserEditForm(instance=user)
        pwd_form = UserSetPasswordForm(user)
    return render(request, "accounts/user_form.html", {"form": form, "pwd_form": pwd_form, "edit_user": user, "create": False, "is_admin": is_admin})

# --- Password reset/change using built-in views ---

class MyPasswordResetView(PasswordResetView):
    template_name = "accounts/password_reset.html"
    email_template_name = "accounts/password_reset_email.txt"
    subject_template_name = "accounts/password_reset_subject.txt"
    success_url = reverse_lazy("password_reset_done")

class MyPasswordResetDoneView(PasswordResetDoneView):
    template_name = "accounts/password_reset_done.html"

class MyPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = "accounts/password_reset_confirm.html"
    success_url = reverse_lazy("password_reset_complete")

class MyPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = "accounts/password_reset_complete.html"

class MyPasswordChangeView(PasswordChangeView):
    template_name = "accounts/password_change.html"
    success_url = reverse_lazy("password_change_done")

class MyPasswordChangeDoneView(PasswordChangeDoneView):
    template_name = "accounts/password_change_done.html"

# views.py
from datetime import date, datetime, timedelta
from collections import Counter, defaultdict

from django.db.models import Count, Q, F, Value
from django.db.models.functions import Coalesce, TruncMonth, TruncWeek
from django.http import HttpRequest, HttpResponse, StreamingHttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
try:
    from followup.models import FollowUpCase, CaseTask
except Exception:
    FollowUpCase = CaseTask = None

# Adjust these to your app paths
from member.models import Member, Family, Campus
try:
    # You said AuditLog lives in audit.py, not models.py
    from member.audit import AuditLog
except Exception:
    AuditLog = None  # template will degrade gracefully

# Optional attendance app
try:
    from attendance.models import Attendance  # expected fields: member(FK), attended_at(Date/DateTime)
except Exception:
    Attendance = None

try:
    from events.models import EventRegistration, Guest, Event
except Exception:
    EventRegistration = None
    Guest = None
    Event = None

# -------- helpers --------

def _parse_iso_date(s: str | None) -> date | None:
    if not s:
        return None
    try:
        # Accept YYYY-MM-DD (browser date input)
        return datetime.fromisoformat(s).date()
    except ValueError:
        return None

def _daterange_from_get(request: HttpRequest):
    """Return (start_dt, end_dt_exclusive) in local timezone for filtering created_at/when."""
    tz = timezone.get_current_timezone()
    start = _parse_iso_date(request.GET.get("start"))
    end = _parse_iso_date(request.GET.get("end"))

    if start and end and end < start:
        # swap if user flipped them
        start, end = end, start

    if start:
        start_dt = tz.localize(datetime.combine(start, datetime.min.time()))
    else:
        # default: last 90 days
        start_dt = timezone.now() - timedelta(days=90)

    if end:
        # make end exclusive (end of day +1)
        end_dt = tz.localize(datetime.combine(end, datetime.min.time())) + timedelta(days=1)
    else:
        end_dt = timezone.now() + timedelta(days=1)

    return start_dt, end_dt

def _age_years(dob: date, today: date) -> int:
    if not dob:
        return -1
    years = today.year - dob.year
    if (today.month, today.day) < (dob.month, dob.day):
        years -= 1
    return years

def _age_bucket(age: int) -> str:
    if age < 0:
        return "-"
    if age < 13:   return "0-12"
    if age < 18:   return "13-17"
    if age < 25:   return "18-24"
    if age < 35:   return "25-34"
    if age < 45:   return "35-44"
    if age < 60:   return "45-59"
    return "60+"

# -------- main dashboard --------
@login_required
def dashboard(request: HttpRequest) -> HttpResponse:
    tz = timezone.get_current_timezone()
    now = timezone.now().astimezone(tz)
    today = now.date()

    start_dt, end_dt = _daterange_from_get(request)
    campus_id = request.GET.get("campus") or ""

    # Base filters
    member_filter = Q()
    family_filter = Q()
    activity_filter = Q()

    # date window applied to reasonable fields
    member_filter &= Q(created_at__gte=start_dt, created_at__lt=end_dt)
    family_filter &= Q(created_at__gte=start_dt, created_at__lt=end_dt)
    if AuditLog:
        activity_filter &= Q(when__gte=start_dt, when__lt=end_dt)

    # campus filter
    if campus_id:
        member_filter &= Q(campus_id=campus_id)
        family_member_filter = Q(members__campus_id=campus_id)
    else:
        family_member_filter = Q()  # no restriction

    # ---- KPIs ----
    # total counts (not constrained to date window unless you want them to-usually totals are global)
    total_members = Member.objects.all().count()
    total_families = Family.objects.all().count()

    # new in the week (rolling last 7 days)
    week_ago = now - timedelta(days=7)
    new_members_week = Member.objects.filter(created_at__gte=week_ago).count()
    new_families_week = Family.objects.filter(created_at__gte=week_ago).count()

    # active this month (example: members created in last 30d)
    active_window = now - timedelta(days=30)
    active_this_month = Member.objects.filter(created_at__gte=active_window).count()

    # ---- recent activity ----
    recent_activity = []
    if AuditLog:
        qs_activity = (
            AuditLog.objects
            .select_related(None)
            .filter(activity_filter)
            .order_by("-when")[:25]
        )
        # expected fields: icon, label, url, verb, changes_count, when
        recent_activity = list(qs_activity)

    # ---- lists: recent members & families (respect campus filter if provided) ----
    recent_members = (
        Member.objects
        .select_related("family", "campus")
        .only("uid", "first_name", "last_name", "created_at", "family__name", "campus__name", "photo")
        .filter(member_filter)
        .order_by("-created_at")[:25]
    )

    recent_families = (
        Family.objects
        .only("id", "name", "state_of_residence", "country_of_residence", "created_at")
        .filter(family_filter | family_member_filter)  # show families created now OR that have members in campus/time window
        .order_by("-created_at")[:25]
    )

    # ---- recent guests & registrations / check-ins ----
    recent_guests = []
    if Guest:
        recent_guests = list(Guest.objects.order_by("-updated_at")[:15])

    recent_registrations = []
    if EventRegistration:
        rq = (EventRegistration.objects
              .select_related("event", "member", "guest")
              .order_by("-registered_at")[:15])
        recent_registrations = list(rq)

    recent_checkins = []
    if Attendance:
        aq = (Attendance.objects
              .filter(member__isnull=False)
              .select_related("member", "event")
              .order_by("-checked_in_at")[:15])
        recent_checkins = list(aq)

    # ---- by status / gender (respect campus/date window) ----
    qs_members_window = Member.objects.filter(member_filter)

    by_status = (
        qs_members_window
        .values("status")
        .annotate(count=Count("id"))
        .order_by()
    )
    by_gender = (
        qs_members_window
        .values("gender")
        .annotate(count=Count("id"))
        .order_by()
    )

    # ---- top campuses (global or filtered?) usually show global snapshot, but you asked "top 8 with membersâ€
    by_campus = (
        Member.objects
        .values("campus__name")
        .annotate(count=Count("id"))
        .order_by("-count")[:8]
    )

    # ---- monthly new members (last 12 months, global snapshot or filtered by campus?) ----
    months_back = 12
    monthly_qs = Member.objects.all()
    if campus_id:
        monthly_qs = monthly_qs.filter(campus_id=campus_id)

    by_month = (
        monthly_qs
        .annotate(month=TruncMonth("created_at", tzinfo=tz))
        .values("month")
        .annotate(count=Count("id"))
        .order_by("month")
    )

    # ---- age buckets (compute in Python to avoid DB-specific expressions) ----
    by_age = []
    try:
        members_with_dob = Member.objects.filter(dob__isnull=False)
        if campus_id:
            members_with_dob = members_with_dob.filter(campus_id=campus_id)
        ages = [_age_years(m.dob, today) for m in members_with_dob.only("dob", "campus")]
        counter = Counter(_age_bucket(a) for a in ages)
        # Stable order of buckets
        buckets = ["0-12", "13-17", "18-24", "25-34", "35-44", "45-59", "60+", "-"]
        by_age = [{"bucket": b, "count": counter.get(b, 0)} for b in buckets if counter.get(b, 0) or b != "-"]
    except Exception:
        by_age = []

    # ---- birthdays (current month) ----
    upcoming_birthdays = (
        Member.objects
        .filter(dob__isnull=False, dob__month=today.month)
        .only("uid", "first_name", "last_name", "dob")
    )
    if campus_id:
        upcoming_birthdays = upcoming_birthdays.filter(campus_id=campus_id)
    # annotate age (in Python)
    _b = []
    for m in upcoming_birthdays:
        _b.append({
            "uid": m.uid,
            "first_name": m.first_name,
            "last_name": m.last_name,
            "dob": m.dob,
            "age": _age_years(m.dob, today),
        })
    upcoming_birthdays = _b

    # ---- attendance last 8 weeks (optional) ----
    attendance_summary = []
    if Attendance:
        att_qs = Attendance.objects.all()
        if campus_id:
            att_qs = att_qs.filter(member__campus_id=campus_id)
        eight_weeks_ago = now - timedelta(weeks=8)
        att_qs = att_qs.filter(attended_at__gte=eight_weeks_ago, attended_at__lt=now + timedelta(days=1))
        weekly = (
            att_qs
            .annotate(week=TruncWeek("attended_at", tzinfo=tz))
            .values("week")
            .annotate(count=Count("id"))
            .order_by("week")
        )
        attendance_summary = [{"week": w["week"].strftime("%G-W%V"), "count": w["count"]} for w in weekly]

    # ---- campuses for filter select ----
    campuses = list(Campus.objects.only("id", "name").order_by("name"))

    # ---- insights (example placeholders; adjust to your real logic) ----
    # retention_30d: % of members created >30d ago who still have status!=new (dummy proxy)
    try:
        thirty_days_ago = now - timedelta(days=30)
        cohort = Member.objects.filter(created_at__lt=thirty_days_ago).count()
        retained = Member.objects.filter(created_at__lt=thirty_days_ago).exclude(status="new").count()
        retention_30d = f"{(retained / cohort * 100):.0f}%" if cohort else "-"
    except Exception:
        retention_30d = "-"

    # conversions (examples)
    try:
        total = Member.objects.all().count()
        conversion_worker = f"{(Member.objects.filter(status='worker').count() / total * 100):.0f}%" if total else "-"
        conversion_leader = f"{(Member.objects.filter(status='leader').count() / total * 100):.0f}%" if total else "-"
    except Exception:
        conversion_worker = conversion_leader = "-"

    # ---- export URL (wire to CSV view below) ----
    export_url = reverse("dashboard_export") + (f"?start={request.GET.get('start','')}&end={request.GET.get('end','')}&campus={campus_id}" if (request.GET.get('start') or request.GET.get('end') or campus_id) else "")

    context = {
        # Filters
        "campuses": campuses,
        # KPIs
        "total_members": total_members,
        "total_families": total_families,
        "new_members_week": new_members_week,
        "new_families_week": new_families_week,
        "active_this_month": active_this_month,
        # Lists
        "recent_activity": recent_activity,
        "recent_members": recent_members,
        "recent_families": recent_families,
        "recent_guests": recent_guests,
        "recent_registrations": recent_registrations,
        "recent_checkins": recent_checkins,
        # Charts / aggregates
        "by_status": list(by_status),
        "by_gender": list(by_gender),
        "by_campus": list(by_campus),
        "by_month": [{"month": (r["month"].strftime("%Y-%m") if r["month"] else "-"), "count": r["count"]} for r in by_month],
        "by_age": by_age,
        "attendance_summary": attendance_summary,
        # Birthdays & insights
        "upcoming_birthdays": upcoming_birthdays,
        "retention_30d": retention_30d,
        "conversion_worker": conversion_worker,
        "conversion_leader": conversion_leader,
        # Export
        "export_url": export_url,
        # My follow-up (lightweight)
        "my_followup": None,
        }
    # Enrich with follow-up KPIs for the current user
    if request.user.is_authenticated and FollowUpCase and CaseTask:
        try:
            OPEN = ["new","open","hold"]
            now = timezone.now()
            fc = FollowUpCase.objects.filter(assigned_to=request.user, status__in=OPEN)
            tk = CaseTask.objects.filter(case__assigned_to=request.user, is_done=False)
            context["my_followup"] = {
                "cases_open": fc.count(),
                "cases_overdue": fc.filter(due_at__lt=now).count(),
                "tasks_pending": tk.count(),
                "tasks_due_today": tk.filter(due_at__date=now.date()).count(),
                "top_tasks": list(tk.order_by("due_at")[:5]),
            }
        except Exception:
            context["my_followup"] = None
    return render(request, "dashboard.html", context)

# -------- simple CSV export for the toolbar --------

import csv
from io import StringIO

def dashboard_export_csv(request: HttpRequest) -> HttpResponse:
    """
    Example export: dumps members matching the same filter window + campus as a flat CSV
    Customize columns as you like.
    """
    start_dt, end_dt = _daterange_from_get(request)
    campus_id = request.GET.get("campus") or ""

    qs = Member.objects.filter(created_at__gte=start_dt, created_at__lt=end_dt)
    if campus_id:
        qs = qs.filter(campus_id=campus_id)

    qs = qs.select_related("family", "campus").only(
        "uid", "first_name", "last_name", "gender", "status", "created_at",
        "dob", "family__name", "campus__name"
    ).order_by("-created_at")

    # Stream as CSV
    def row_iter():
        header = ["UID", "First Name", "Last Name", "Gender", "Status", "dob", "Family", "Campus", "Created At"]
        yield header
        for m in qs.iterator(chunk_size=1000):
            yield [
                str(m.uid),
                m.first_name or "",
                m.last_name or "",
                m.gender or "",
                m.status or "",
                m.dob.isoformat() if getattr(m, "dob", None) else "",
                m.family.name if m.family_id else "",
                m.campus.name if m.campus_id else "",
                timezone.localtime(m.created_at).strftime("%Y-%m-%d %H:%M"),
            ]

    class Echo:
        def write(self, value): return value

    pseudo_buffer = Echo()
    writer = csv.writer(pseudo_buffer)
    response = StreamingHttpResponse((writer.writerow(r) for r in row_iter()), content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="members_export.csv"'
    return response

