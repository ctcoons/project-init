import tempfile
import json
import os
from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import FileResponse, JsonResponse
from .forms import SignUpForm, ProjectDataForm, UploadExcelForm
from .models import ProjectData
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


# ----------------- Project creation -----------------
@login_required
def create_project(request):
    if request.method == 'POST':
        form = ProjectDataForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.owner = request.user
            project.save()
            return redirect('project_list')
    else:
        form = ProjectDataForm()
    return render(request, 'core/create_project.html', {'form': form})


@login_required
def project_list(request):
    projects = ProjectData.objects.all()
    return render(request, 'core/project_list.html', {'projects': projects})


# ----------------- Start project & download Excel -----------------
@login_required
def start_project(request):
    if request.method == "POST":
        project_name = request.POST.get("project_name")
        description = request.POST.get("description")
        num_groups = int(request.POST.get("num_groups"))
        groups = [request.POST.get(f"group_{i}") for i in range(1, num_groups + 1)]

        # Save project in DB
        project_model = ProjectData(
            owner=request.user,
            project_name=project_name,
            description=description,
            number_of_groups=num_groups,
            group_names=",".join(groups)
        )
        project_model.save()

        # Prepare Python object for Excel generator
        project_data = ExcelProjectData(
            name=project_model.project_name,
            owner=request.user.username,
            description=project_model.description,
            groups=groups
        )

        generator = ExcelFileGenerator()
        file_path = generator.make_new_file_from_template_with_openpyxl(
            project_data, output_name=project_name
        )

        # Send file directly to browser
        return FileResponse(
            open(file_path, "rb"),
            as_attachment=True,
            filename=os.path.basename(file_path)
        )

    return render(request, "core/start_project.html")


# ----------------- Upload Excel preview -----------------
@login_required
def upload_preview(request):
    if request.method == "POST" and request.FILES.get("file"):
        excel_file = request.FILES["file"]

        # Use FileReader to parse Excel
        reader = FileReader()
        project_data = ExcelProjectData(name="Temp", owner=request.user.username, description="", groups=[])
        response: FileReaderResponse = reader.get_file_reader_response(project_data, excel_file)

        # Convert to JSON-serializable dict
        response_dict = {
            "success": response.was_successful(),
            "message": response.get_message(),
            "data": response.get_data(),
            "independent_variables": response.get_independent_variables(),
            "possible_typos": response.get_possible_typos(),
            "project_name": response.get_project_data().get_name(),
            "groups": response.get_project_data().get_groups()
        }
        return JsonResponse(response_dict)

    return JsonResponse({"error": "No file provided"}, status=400)


# ----------------- Confirm upload and save to DB -----------------
@login_required
@csrf_exempt
def upload_project(request):
    if request.method == "POST":
        try:
            body = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        file_response = body.get("file_response")
        if not file_response:
            return JsonResponse({"error": "No file_response provided"}, status=400)

        project_name = file_response.get("project_name", "Untitled")
        groups = file_response.get("groups", [])
        data = file_response.get("data", {})

        # Create the ProjectData entry
        project_model = ProjectData(
            owner=request.user,
            project_name=project_name,
            description="",
            number_of_groups=len(groups),
            group_names=",".join(groups)
        )
        project_model.save()

        # Save each group/category/label/value
        from .models import GroupData
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

        return JsonResponse({"success": True})

    return JsonResponse({"error": "Invalid request"}, status=400)
