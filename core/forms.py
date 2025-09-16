from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import ProjectData, ProjectFile, Subject


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
    csv_file = forms.FileField(
        label="Select CSV file",
        widget=forms.ClearableFileInput(attrs={'accept': '.csv'})
    )


class SubjectSelectionForm(forms.Form):
    subjects = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

    def __init__(self, *args, **kwargs):
        subjects = kwargs.pop("subjects", [])
        super().__init__(*args, **kwargs)
        self.fields["subjects"].choices = [
            (i, f"Row {i+1}") for i, _ in enumerate(subjects)
        ]


class ProjectFileForm(forms.ModelForm):
    class Meta:
        model = ProjectFile
        fields = ["file", "visibility"]


class ProjectSettingsForm(forms.ModelForm):
    class Meta:
        model = ProjectData
        fields = ['project_name']
        widgets = {
            'project_name': forms.TextInput(attrs={'class': 'form-control'}),
        }

