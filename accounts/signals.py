from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db.models.signals import m2m_changed
from django.dispatch import receiver


STAFF_GROUP_NAMES = {"Admin", "IT Support"}


def _recompute_staff_flag(user):
    try:
        group_names = set(user.groups.values_list("name", flat=True))
        should_be_staff = bool(group_names & STAFF_GROUP_NAMES)
        # Keep superusers staff regardless; unset only if not superuser and no staff groups
        new_flag = True if (user.is_superuser or should_be_staff) else False
        if user.is_staff != new_flag:
            user.is_staff = new_flag
            user.save(update_fields=["is_staff"])
    except Exception:
        # Avoid noisy crashes from signals
        pass


@receiver(m2m_changed, sender=get_user_model().groups.through)
def user_groups_changed(sender, instance, action, **kwargs):
    if action in {"post_add", "post_remove", "post_clear"}:
        _recompute_staff_flag(instance)
