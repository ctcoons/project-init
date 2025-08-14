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
        fields = ['project_name', 'description', 'number_of_groups', 'group_names']
        widgets = {
            'group_names': forms.Textarea(attrs={'rows': 3}),
            'description': forms.Textarea(attrs={'rows': 4}),
        }


class UploadExcelForm(forms.Form):
    excel_file = forms.FileField(label="Upload Completed Excel File")
