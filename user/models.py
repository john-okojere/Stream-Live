from django.db import models
from django.contrib.auth.models import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.utils import timezone
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.validators import RegexValidator
import uuid
from .manager import UserManager

from django.urls import reverse
import os

GENDER_CATEGORY=(
    ('Male','Male'),
    ('Female','Female'),
)
levels = (
    (1, 1),
    (2, 2), 
    (3, 3),
    (4, 4),
    (5, 5),
)

CHURCH_ROLES = (
    ("AHS", "Asst. Head Steward"),
    ("AdminPastor", "Admin Pastor"),
    ("ResidentPastor", "Resident Pastor"),
    ("AssistantResidentPastor", "Asst. Resident Pastor"),
    ("InhousePastor", "Inhouse Pastor"),
    ("Worker", "Worker"),

    ("SuperAdmin", "Super Admin"),
    ("SeniorPastor", "Senior Pastor"),
    ("ChurchAdmin", "Church Administrator"),
    ("FinanceOfficer", "Finance Officer"),
    ("HROfficer", "HR Officer"),
    ("ITSupport", "IT Support"),

    ("DepartmentHead", "Department Head"),
    ("CellLeader", "Cell Leader"),
    ("GroupAdmin", "Group Admin"),
    ("VolunteerLeader", "Volunteer Leader"),

    ("ChoirDirector", "Choir Director"),
    ("PrayerCoordinator", "Prayer Coordinator"),
    ("MediaTeamLead", "Media Team Lead"),
    ("ProtocolOfficer", "Protocol Officer"),

    ("Member", "Member"),
    ("NewConvert", "New Convert"),
    ("BaptismCandidate", "Baptism Candidate"),
    ("DiscipleshipStudent", "Discipleship Student"),

    ("PastoralAssistant", "Pastoral Assistant"),
    ("EventsCoordinator", "Events Coordinator"),
    ("SecurityTeamLead", "Security Team Lead"),
    ("ChildrenChurchLead", "Children Church Lead"),
    ("TechnicalDirector", "Technical Director"),
    ("FollowUpOfficer", "Follow-Up Officer"),
)

class User(AbstractBaseUser, PermissionsMixin):
    uid = models.UUIDField( default=uuid.uuid4, editable=False)
    first_name = models.CharField(verbose_name='first name', max_length=150, blank=True)
    last_name = models.CharField(verbose_name='last name', max_length=150, blank=True)
    phone_regex = RegexValidator(regex=r'^\+\d{8,15}$|^0\d{10}$', message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.")
    phone = models.CharField(
        validators=[phone_regex],
        max_length=16,
        unique=True,
        help_text="Phone number must be entered in the format: '+999999999'.",
        error_messages={
            'unique': "This Phone has been used already",
        },
        ) # validators should be a list
    email = models.EmailField(verbose_name='email address', unique=True,
        error_messages={
            'unique': "This email has been used already",
        },
    )

    gender = models.CharField(max_length= 20, choices=GENDER_CATEGORY)
    date_of_birth = models.DateField(null=True)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    level = models.IntegerField(choices=levels, default=1)
    date_joined = models.DateTimeField(default=timezone.now)
    update_fields = models.DateTimeField(auto_now=True)

    EMAIL_FIELD = 'email'
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['phone']

    objects = UserManager()

    def full_name(self):
        return f'{self.last_name} {self.first_name}'
       
    def get_absolute_url(self):
        return reverse("profile", kwargs={"uid": self.uid}) 
    

    def __str__(self):
        return str(self.last_name + " " +self.first_name)

