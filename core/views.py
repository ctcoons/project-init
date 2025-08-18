import csv
import io
import tempfile
import json
import os
from collections import defaultdict
from functools import wraps

from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import FileResponse, JsonResponse, HttpResponseForbidden
from openpyxl.pivot.cache import GroupItems

from .forms import SignUpForm, ProjectDataForm, UploadExcelForm, CSVUploadForm, SubjectSelectionForm
from .models import ProjectData, GroupData, GroupSubData, Subject
from core.utils.excel.excel_file_generation import ExcelFileGenerator
from core.utils.excel.project_data import FileReaderProjectData as ExcelProjectData
from .utils.excel.file_reader import FileReader, FileReaderResponse


def project_owner_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, project_id, *args, **kwargs):
        project = get_object_or_404(ProjectData, id=project_id)
        if project.owner != request.user:
            return HttpResponseForbidden("You are not allowed to access this project.")
        return view_func(request, project_id, *args, **kwargs)
    return _wrapped_view


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
        response_dict = make_json_safe(response_dict)

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
        independent_variables = file_response.get("independent_variables", {})

        # Save each group/category/label/value
        for group_name, categories in data.items():
            group_instance = GroupData.objects.create(
                project=project_model,
                group_name=group_name
            )
            for category_name, labels in categories.items():
                for label, value in labels.items():
                    GroupSubData.objects.create(
                        group=group_instance,
                        category=category_name,
                        label=label,
                        value=value
                    )

        if independent_variables:
            project_model.independent_variable = {
                str(k): list(map(str, v)) for k, v in independent_variables.items()
            }
            project_model.save()

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


def make_json_safe(obj):
    """
    Recursively convert defaultdicts and other non-JSON-safe types
    into regular dicts/lists/strings so they can be serialized by JsonResponse.
    """
    if isinstance(obj, defaultdict):
        return {k: make_json_safe(v) for k, v in obj.items()}
    elif isinstance(obj, dict):
        return {k: make_json_safe(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [make_json_safe(v) for v in obj]
    elif hasattr(obj, "__dict__"):  # for custom classes (like ProjectData)
        return make_json_safe(obj.__dict__)
    else:
        return obj


# ----------------- Add Subject Data -----------------
@project_owner_required
@login_required
def add_subject_data(request, project_id):
    project = get_object_or_404(ProjectData, id=project_id)
    groups = project.group_data.all()

    subjects = request.session.get("subjects_preview", [])

    # Step 1: Upload CSV
    if request.method == "POST" and "upload_csv" in request.POST:
        form = CSVUploadForm(request.POST, request.FILES)
        if form.is_valid():
            file = form.cleaned_data["file"]
            decoded = file.read().decode("utf-8")
            import csv, io
            reader = csv.DictReader(io.StringIO(decoded))
            subjects = list(reader)
            request.session["subjects_preview"] = subjects
            selection_form = SubjectSelectionForm(groups=groups, subjects=subjects)
        else:
            selection_form = None

    # Step 2: Add selected subjects
    elif request.method == "POST" and "add_subjects" in request.POST:
        selection_form = SubjectSelectionForm(request.POST, groups=groups, subjects=subjects)
        if selection_form.is_valid():
            group_id = selection_form.cleaned_data["group"]
            selected_indexes = selection_form.cleaned_data["subjects"]
            group = get_object_or_404(GroupData, id=group_id)
            added = 0

            for idx in selected_indexes:
                data = subjects[int(idx)]
                Subject.objects.create(group=group, metadata=data)
                added += 1

            # Update session to remove added subjects
            subjects = [s for i, s in enumerate(subjects) if str(i) not in selected_indexes]
            request.session["subjects_preview"] = subjects

            messages.success(request, f"Successfully added {added} subjects to {group.group_name}.")
            return redirect("add_subject_data", project_id=project.id)
    else:
        # GET request
        selection_form = None if not subjects else SubjectSelectionForm(groups=groups, subjects=subjects)

    return render(request, "core/add_subject_data.html", {
        "project": project,
        "upload_form": CSVUploadForm(),
        "selection_form": selection_form,
        "subjects": subjects,
    })

