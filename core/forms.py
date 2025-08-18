from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import ProjectData


class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")


class ProjectDataForm(forms.ModelForm):
    class Meta:
        model = ProjectData
        fields = ['project_name', 'description', 'number_of_groups']
        widgets = {
            'project_name': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_project_name'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'id': 'id_description'}),
        }


class UploadExcelForm(forms.Form):
    excel_file = forms.FileField(label="Upload Completed Excel File")


class CSVUploadForm(forms.Form):
    file = forms.FileField(label="Upload CSV")


class SubjectSelectionForm(forms.Form):
    group = forms.ChoiceField(choices=[], required=True)
    subjects = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple, required=False)

    def __init__(self, *args, **kwargs):
        groups = kwargs.pop("groups", [])
        subjects = kwargs.pop("subjects", [])
        super().__init__(*args, **kwargs)
        self.fields["group"].choices = [(g.id, g.group_name) for g in groups]
        self.fields["subjects"].choices = [(i, f"Row {i+1}") for i, _ in enumerate(subjects)]