from django import forms
from .models import Sermon

class SermonForm(forms.ModelForm):
    class Meta:
        model = Sermon
        fields = ["title", "speaker", "date", "description", "tags", "cover", "audio"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),  # HTML5 date picker
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ensure correct display/parse format
        self.fields["date"].widget.format = "%Y-%m-%d"
        self.fields["date"].input_formats = ["%Y-%m-%d"]
