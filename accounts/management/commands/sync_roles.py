from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

# Models to map permissions for
from accounts.models import User
from member.models import Campus, Family, Member, Department, DepartmentMembership
from events.models import Event, EventRegistration, Guest, WomenFellowshipGroup, WomenFellowshipMembership
from attendance.models import Attendance
from cards.models import MemberCard, CardValidationLog
from support.models import Applicant, Invite, SupportTeamMember, OnboardingTask, StaffNote
from followup.models import FollowUpCase, CaseNote, CaseTask, CaseAttachment, ActivityLog
from mailer.models import Campaign, CampaignAttachment, CampaignRecipient


def perms_for_models(*models, actions=("view", "add", "change")):
    """Yield Permission objects for the given Django models and action codenames.

    By default includes 'view', 'add', 'change'. Use actions=(...) to customize.
    """
    wanted = set(actions)
    for model in models:
        ct = ContentType.objects.get_for_model(model)
        # Model perm codenames are <action>_<modelname>
        qs = Permission.objects.filter(content_type=ct)
        for p in qs:
            try:
                action, _ = p.codename.split("_", 1)
            except ValueError:
                continue
            if action in wanted:
                yield p


class Command(BaseCommand):
    help = "Create core role groups (Admin, IT Support, Socials) and assign permissions"

    def handle(self, *args, **options):
        # Create groups
        admin_group, _ = Group.objects.get_or_create(name="Admin")
        it_group, _ = Group.objects.get_or_create(name="IT Support")
        socials_group, _ = Group.objects.get_or_create(name="Socials")

        # Admin: all permissions
        all_perms = Permission.objects.all()
        admin_group.permissions.set(all_perms)

        # IT Support: broad operational access across core apps
        it_perms = set()
        #  allow password resets but not full user admin UI
        it_perms.update(perms_for_models(User, actions=("change",)))
        # People directory
        it_perms.update(perms_for_models(Campus, Family, Member, Department, DepartmentMembership))
        # Events + Attendance
        it_perms.update(perms_for_models(Event, EventRegistration, Guest))
        it_perms.update(perms_for_models(WomenFellowshipGroup, WomenFellowshipMembership))
        it_perms.update(perms_for_models(Attendance))
        # Cards (incl. view logs)
        it_perms.update(perms_for_models(MemberCard))
        it_perms.update(perms_for_models(CardValidationLog, actions=("view",)))
        # Support (onboarding via application)
        it_perms.update(perms_for_models(Applicant, Invite, SupportTeamMember, OnboardingTask, StaffNote))

        # Follow-up: allow IT Support to view follow-up entities
        it_perms.update(perms_for_models(FollowUpCase, actions=("view",)))
        it_perms.update(perms_for_models(CaseNote, actions=("view",)))
        it_perms.update(perms_for_models(CaseTask, actions=("view",)))
        it_perms.update(perms_for_models(CaseAttachment, actions=("view",)))
        it_perms.update(perms_for_models(ActivityLog, actions=("view",)))

        it_group.permissions.set(it_perms)

        # Socials: bulk email tool (mailer)
        socials_perms = set()
        socials_perms.update(perms_for_models(Campaign, CampaignAttachment, CampaignRecipient, actions=("view", "add", "change", "delete")))
        socials_group.permissions.set(socials_perms)

        self.stdout.write(self.style.SUCCESS("Synced role groups: Admin, IT Support, Socials"))
