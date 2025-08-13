from django.shortcuts import render, redirect
from django.contrib.auth import login
from .forms import SignUpForm, ProjectDataForm
from django.contrib.auth.decorators import login_required
from .models import ProjectData
import os
from django.http import FileResponse
from core.utils.excel.excel_file_generation import ExcelFileGenerator
from core.utils.excel.project_data import ProjectData as ExcelProjectData




def register(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)  # log in the user right after registering
            return redirect('home')  # redirect to homepage (we’ll create this soon)
    else:
        form = SignUpForm()
    return render(request, 'registration/register.html', {'form': form})


@login_required
def home(request):
    return render(request, 'registration/home.html')


@login_required
def create_project(request):
    if request.method == 'POST':
        form = ProjectDataForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.owner = request.user  # assign the logged-in user as owner
            project.save()
            return redirect('project_list')  # we’ll make this next
    else:
        form = ProjectDataForm()
    return render(request, 'core/create_project.html', {'form': form})


@login_required
def project_list(request):
    projects = ProjectData.objects.all()
    return render(request, 'core/project_list.html', {'projects': projects})


@login_required
def start_project(request):
    if request.method == "POST":
        print("Posting....")
        project_name = request.POST.get("project_name")
        description = request.POST.get("description")
        num_groups = int(request.POST.get("num_groups"))
        groups = [request.POST.get(f"group_{i}") for i in range(1, num_groups + 1)]

        project_data = ExcelProjectData(
            name=project_name,
            owner=request.user.username,
            description=description,
            groups=groups
        )

        generator = ExcelFileGenerator()
        file_path = generator.make_new_file_from_template_with_openpyxl(project_data, output_name=project_name)

        return FileResponse(open(file_path, "rb"), as_attachment=True, filename=os.path.basename(file_path))

    # GET request just renders form (no session flag)
    return render(request, "core/start_project.html")


@login_required
def upload_data(request):
    # your upload handling code here
    return render(request, 'core/upload.html')

