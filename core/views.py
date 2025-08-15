import tempfile
import json
import os
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import FileResponse, JsonResponse
from .forms import SignUpForm, ProjectDataForm, UploadExcelForm
from .models import ProjectData, GroupData
from core.utils.excel.excel_file_generation import ExcelFileGenerator
from core.utils.excel.project_data import FileReaderProjectData as ExcelProjectData
from .utils.excel.file_reader import FileReader, FileReaderResponse


# ----------------- User registration & home -----------------
def register(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
    else:
        form = SignUpForm()
    return render(request, 'registration/register.html', {'form': form})


@login_required
def home(request):
    return render(request, 'registration/home.html')


# ----------------- List Projects -----------------

@login_required
def project_list(request):
    projects = ProjectData.objects.all()
    return render(request, 'core/project_list.html', {'projects': projects})


# ----------------- Create Project / Start Project -----------------
@login_required
def start_project(request):
    if request.method == "POST":
        form = ProjectDataForm(request.POST)
        if form.is_valid():
            # Save basic project
            project_model = form.save(commit=False)
            project_model.owner = request.user
            project_model.number_of_groups = int(request.POST.get("number_of_groups", 0))

            # Collect dynamic group names
            groups = [request.POST.get(f"group_{i}") for i in range(1, project_model.number_of_groups + 1)]
            project_model.group_names = ",".join(groups)
            project_model.save()

            # Prepare Excel data
            project_data = ExcelProjectData(
                name=project_model.project_name,
                owner=request.user.username,
                description=project_model.description,
                groups=groups
            )
            generator = ExcelFileGenerator()
            file_path = generator.make_new_file_from_template_with_openpyxl(
                project_data, output_name=project_model.project_name
            )

            # Store project ID in session for upload confirmation later
            request.session['pending_project_id'] = project_model.id

            return FileResponse(
                open(file_path, "rb"),
                as_attachment=True,
                filename=os.path.basename(file_path)
            )

    else:
        form = ProjectDataForm()

    return render(request, "core/start_project.html", {"form": form})


# ----------------- Upload Excel Preview -----------------
@login_required
def upload_excel_preview(request):
    if request.method == "POST" and request.FILES.get("file"):
        excel_file = request.FILES["file"]

        # Get the pending project ID
        project_id = request.session.get("pending_project_id")
        if not project_id:
            return JsonResponse({"success": False, "message": "No pending project found."})

        project_model = get_object_or_404(ProjectData, id=project_id)
        project_data = ExcelProjectData(
            name=project_model.project_name,
            owner=request.user.username,
            description=project_model.description,
            groups=project_model.group_names.split(",")
        )

        reader = FileReader()
        response: FileReaderResponse = reader.get_file_reader_response(project_data, excel_file)

        response_dict = {
            "success": response.was_successful(),
            "message": response.get_message(),
            "data": response.get_data(),
            "independent_variables": response.get_independent_variables(),
            "typos": response.get_possible_typos(),
            "project_name": response.get_project_data().get_name(),
            "groups": response.get_project_data().get_groups()
        }
        # Store the file response in session for confirmation
        request.session['file_response'] = response_dict
        return JsonResponse(response_dict)

    return JsonResponse({"success": False, "message": "No file provided"})


# ----------------- Confirm Excel Upload -----------------
@login_required
@csrf_exempt
def upload_excel_confirm(request):
    if request.method == "POST":
        project_id = request.session.get("pending_project_id")
        file_response = request.session.get("file_response")
        if not project_id or not file_response:
            return JsonResponse({"success": False, "message": "No pending project or file response found."})

        project_model = get_object_or_404(ProjectData, id=project_id)
        data = file_response.get("data", {})

        # Save each group/category/label/value
        for group_name, categories in data.items():
            for category_name, labels in categories.items():
                for label, value in labels.items():
                    GroupData.objects.create(
                        project=project_model,
                        group_name=group_name,
                        category=category_name,
                        label=label,
                        value=value
                    )

        # Clear session
        del request.session['pending_project_id']
        del request.session['file_response']

        return JsonResponse({"success": True, "redirect_url": f"/project/{project_model.id}/"})

    return JsonResponse({"success": False, "message": "Invalid request"})


# ----------------- Project Detail -----------------
@login_required
def project_detail(request, project_id):
    project = get_object_or_404(ProjectData, id=project_id)
    group_data = project.group_data.all()  # Related name
    return render(request, "core/project_detail.html", {"project": project, "group_data": group_data})