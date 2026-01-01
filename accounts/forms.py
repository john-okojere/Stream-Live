# accounts/forms.py
from django import forms
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.forms import UserCreationForm, SetPasswordForm
from django.contrib.auth.models import Group
from .models import User

class RegisterForm(UserCreationForm):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.fields.values():
            f.widget.attrs.update({"class": "form-control"})
        self.fields["password1"].widget.attrs.update({"placeholder": "Create password"})
        self.fields["password2"].widget.attrs.update({"placeholder": "Confirm password"})


ROLE_GROUP_NAMES = [
    "Admin",
    "IT Support",
    "Socials",
    "Followup Supervisors",
    "Followup Agents",
]


class UserCreateWithRolesForm(RegisterForm):
    groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.filter(name__in=ROLE_GROUP_NAMES).order_by("name"),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text="Assign one or more roles to this user.",
    )
    is_active = forms.BooleanField(initial=True, required=False)

    class Meta(RegisterForm.Meta):
        model = User
        fields = ("first_name", "last_name", "email", "password1", "password2", "is_active", "groups")


class UserEditForm(forms.ModelForm):
    groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.filter(name__in=ROLE_GROUP_NAMES).order_by("name"),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text="Assign roles",
    )

    class Meta:
        model = User
        fields = ("first_name", "last_name", "email", "is_active", "groups")
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Preselect current groups
        if self.instance and self.instance.pk:
            self.fields["groups"].initial = self.instance.groups.filter(name__in=ROLE_GROUP_NAMES).all()


class UserSetPasswordForm(SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.fields.values():
            f.widget.attrs.update({"class": "form-control"})

class EmailAuthenticationForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={"class":"form-control","placeholder":"name@example.com"}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={"class":"form-control","placeholder":"Password"}))

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self.user_cache = None
        super().__init__(*args, **kwargs)

    def clean(self):
        email = self.cleaned_data.get("email")
        password = self.cleaned_data.get("password")
        if email and password:
            self.user_cache = authenticate(self.request, email=email, password=password)
            if self.user_cache is None:
                raise forms.ValidationError("Invalid email or password.")
            if not self.user_cache.is_active:
                raise forms.ValidationError("This account is inactive.")
        return self.cleaned_data

    def get_user(self):
        return self.user_cache
