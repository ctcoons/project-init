import os
from collections import defaultdict
from functools import wraps

from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import FileResponse, JsonResponse, HttpResponseForbidden

from .forms import SignUpForm, ProjectDataForm, CSVUploadForm, SubjectSelectionForm, ProjectFileForm, \
    ProjectSettingsForm
from .models import ProjectData, GroupData, GroupSubData, Subject, ProjectFile, ProjectMembership, \
    ProjectJoinToken
from core.utils.excel.excel_file_generation import ExcelFileGenerator
from core.utils.excel.project_data import FileReaderProjectData as ExcelProjectData
from .utils.excel.file_reader import FileReader, FileReaderResponse


# ----------------- Decorators -----------------
def project_role_required(allowed_roles):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, project_id, *args, **kwargs):
            project = get_object_or_404(ProjectData, id=project_id)
            membership = ProjectMembership.objects.filter(user=request.user, project=project).first()

            # Owners always have full access
            if project.owner == request.user:
                return view_func(request, project_id, *args, **kwargs)

            if membership is None or membership.role not in allowed_roles:
                return HttpResponseForbidden("You don't have permission to do this.")

            return view_func(request, project_id, *args, **kwargs)

        return _wrapped_view
    return decorator


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
            project_model.group_names = "\t".join(groups)
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
            groups=project_model.group_names.split("\t")
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
    group_data = project.group_data.all()  # all groups in this project
    subjects = Subject.objects.filter(project=project)  # all subjects linked to this project

    return render(
        request,
        "core/project_detail.html",
        {
            "project": project,
            "group_data": group_data,
            "subjects": subjects,
            "can_edit": project.can_edit(request.user),
        },
    )


# ----------------- View, Add, and Delete Files -----------------
@login_required
def view_files(request, project_id):
    project = get_object_or_404(ProjectData, id=project_id)

    # Owner sees all, others see only public
    if request.user == project.owner:
        files = project.files.all()
    else:
        files = project.files.filter(visibility="public")

    form = None
    if project.can_edit(request.user) and request.method == "POST":
        form = ProjectFileForm(request.POST, request.FILES)
        if form.is_valid():
            new_file = form.save(commit=False)
            new_file.project = project
            new_file.uploaded_by = request.user
            new_file.save()
            return redirect("view_files", project_id=project.id)
    elif project.can_edit(request.user):
        form = ProjectFileForm()

    return render(request, "core/view_files.html", {
        "project": project,
        "files": files,
        "form": form,
    })


@project_role_required(["collaborator"])
@login_required
def delete_file(request, project_id, file_id):
    file = get_object_or_404(ProjectFile, id=file_id)
    if request.user == file.project.owner:
        if file.file:
            file.file.delete()
        file.delete()
    return redirect("view_files", project_id=project_id)


# ----------------- View, Add, and Delete Subject Data -----------------
@project_role_required(["collaborator"])
@login_required
def subject_data_page(request, project_id):
    project = get_object_or_404(ProjectData, id=project_id)
    subjects = project.subjects.all()  # now tied directly to project

    is_authorized = (
        request.user == project.owner or
        ProjectMembership.objects.filter(
            project=project,
            user=request.user,
            role="collaborator"
        ).exists()
    )

    return render(request, "core/subject_data.html", {
        "project": project,
        "subjects": subjects,
        "is_authorized": is_authorized,
    })


@project_role_required(["collaborator"])
@login_required
def add_subject_data(request, project_id):
    project = get_object_or_404(ProjectData, id=project_id)
    session_key = f"subjects_preview_{project_id}"

    # Clear session if first GET visit
    if request.method == "GET":
        request.session.pop(session_key, None)
        subjects = []
        selection_form = None
    else:
        # Use previously uploaded subjects if available
        subjects = request.session.get(session_key, [])

        # Step 1: Upload CSV
        if "upload_csv" in request.POST:
            form = CSVUploadForm(request.POST, request.FILES)
            if form.is_valid():
                file = form.cleaned_data["csv_file"]
                decoded = file.read().decode("utf-8")
                import csv, io
                reader = csv.DictReader(io.StringIO(decoded))
                subjects = list(reader)

                request.session[session_key] = subjects
                selection_form = SubjectSelectionForm(subjects=subjects)
            else:
                selection_form = None

        # Step 2: Add selected subjects
        elif "add_subjects" in request.POST:
            selection_form = SubjectSelectionForm(request.POST, subjects=subjects)
            if selection_form.is_valid():
                selected_indexes = selection_form.cleaned_data["subjects"]
                added = 0

                for idx in selected_indexes:
                    data = subjects[int(idx)]
                    Subject.objects.create(project=project, metadata=data)
                    added += 1

                # Remove added subjects from preview
                subjects = [s for i, s in enumerate(subjects) if str(i) not in selected_indexes]
                request.session[session_key] = subjects

                messages.success(request, f"Successfully added {added} subjects to {project.project_name}.")
                return redirect("add_subject_data", project_id=project.id)

        else:
            # POST but not recognized, still show preview if exists
            selection_form = None if not subjects else SubjectSelectionForm(subjects=subjects)

    return render(request, "core/add_subject_data.html", {
        "project": project,
        "upload_form": CSVUploadForm(),
        "selection_form": selection_form,
        "subjects": subjects,
    })



@project_role_required(["collaborator"])
@login_required
def delete_subject(request, project_id, subject_id):
    project = get_object_or_404(ProjectData, id=project_id)

    is_owner = project.owner == request.user
    is_collaborator = project.memberships.filter(user=request.user, role="collaborator").exists()
    if not (is_owner or is_collaborator):
        return HttpResponseForbidden("You do not have permission to delete this subject.")

    subject = get_object_or_404(Subject, id=subject_id, project=project)

    if request.method == "POST":
        subject.delete()
        messages.success(request, "Subject deleted successfully.")
        return redirect("subject_data", project_id=project.id)

    return redirect("subject_data", project_id=project.id)


# ----------------- Project Settings -----------------
@project_role_required([])
@login_required
def project_settings(request, project_id):
    project = get_object_or_404(ProjectData, id=project_id)

    if project.owner != request.user:
        return HttpResponseForbidden("Only the project owner can access project settings.")

    form = ProjectSettingsForm(instance=project)
    invite_link = None

    if request.method == 'POST':
        if 'save_project' in request.POST:
            form = ProjectSettingsForm(request.POST, instance=project)
            if form.is_valid():
                form.save()
                messages.success(request, "Project updated successfully.")
                return redirect('project_settings', project_id=project.id)
        elif 'delete_project' in request.POST:
            project.delete()
            messages.success(request, "Project deleted successfully.")
            return redirect('project_list')
        elif 'generate_invite' in request.POST:
            join_token = ProjectJoinToken.objects.create(project=project)
            invite_link = request.build_absolute_uri(f"/project/{project.id}/join/{join_token.token}/")
        elif "delete_membership_id" in request.POST:
            mem_id = request.POST.get("delete_membership_id")
            membership_to_delete = get_object_or_404(ProjectMembership, id=mem_id, project=project)

            if membership_to_delete.role == "owner":
                messages.error(request, "You cannot remove the project owner.")
            else:
                membership_to_delete.delete()
                messages.success(request, f"Removed {membership_to_delete.user.username} from collaborators.")

            return redirect("project_settings", project.id)


    collaborators = ProjectMembership.objects.filter(project=project)

    return render(request, 'core/project_settings.html', {
        'project': project,
        'form': form,
        'collaborators': collaborators,
        'invite_link': invite_link,
    })


# ----------------- Receive Invite Link And Join -----------------
@login_required
def join_project(request, project_id, token):
    project = get_object_or_404(ProjectData, id=project_id)
    user = project.owner
    if request.user == user:
        return redirect('project_list')

    # Check the token
    try:
        join_token = ProjectJoinToken.objects.get(project=project, token=token)
    except ProjectJoinToken.DoesNotExist:
        messages.error(request, "This invite link is invalid or has already been used.")
        return redirect('project_list')

    # Check if user is already a member
    if ProjectMembership.objects.filter(user=request.user, project=project).exists():
        messages.info(request, "You are already a member of this project.")
        join_token.delete()  # remove token even if already a member
        return redirect('project_detail', project_id=project.id)

    # Add the user as a collaborator
    ProjectMembership.objects.create(user=request.user, project=project, role='collaborator')
    join_token.delete()  # consume the token

    messages.success(request, f"You have been added as a collaborator to '{project.project_name}'.")
    return redirect('project_detail', project_id=project.id)


# ----------------- About Page -----------------
@login_required
def project_about(request, project_id):
    project = get_object_or_404(ProjectData, id=project_id)
    return render(request, "core/about.html", {"project": project})


# ----------------- About Page -----------------
@login_required
def raw_ms_data(request, project_id):
    project = get_object_or_404(ProjectData, id=project_id)
    return render(request, "core/raw_ms_data.html", {"project": project})


# ----------------- Make Json Safe -----------------
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


# ----------------- Tutorial -----------------
# Number of steps in tutorial
TOTAL_STEPS = 9

# Where the Finish button should go
FINISH_REDIRECT = "start_project"

TUTORIAL_STEPS = [
    {
        "description": "Start Your Project",
        "long_description": "Type the name of your project, and a brief description of what you will be doing in your "
                            "project (less than 100 words)",
    },
    {
        "description": "Set Groups",
        "long_description": "Next, add the number of groups you will be testing and their names. For example, "
                            "if you will be testing 3 groups and the names of these groups are “Placebo”, “Drug A”, "
                            "and “Drug B”, you would add 3 groups where it says “Number of Groups” and put these "
                            "names under “Group1”, “Group2”, and “Group3”",
    },
    {
        "description": "Download Your Data Entry Sheet",
        "long_description": "After you have entered the Project Name, Description, Number of Groups, and Group Names, "
                            "click “Start Project (Download Excel)”. This will download a .xlsm file to your browser "
                            "that you will need to open and fill out",
    },
    {
        "description": "Open and Fill Out the Downloaded File",
        "long_description": "Next, open up the .xlsm file that was dowloaded to your browser. If you don’t have "
                            "Microsoft Excel Desktop, some of the functionality will be lost. Get started filling out "
                            "the data about your groups. Optionally, you can also select presets to the left to "
                            "expedite the data entry process.",
    },
    {
        "description": "(optional) Use Built-In Features",
        "long_description": "Optionally, after filling out one column, you can click this button for a quick copy and "
                            "paste horizontally to the rest of your groups. After this, you can change individual "
                            "cells as needed. ",
    },
    {
        "description": "(optional) Add Custom Variables",
        "long_description": "If you wish to add a variable that isn’t already defined, put the label of that variable "
                            "to the left of the columns that represent the group data, and then put in the values "
                            "that correspond to each group. For example, in you could add “Drug Given” as a category, "
                            "with “Placebo”, “Drug A”, and “Drug B” as values. (Alternatively this could be put under "
                            "“Treatment”) ",
    },
    {
        "description": "Continue To Enter Data",
        "long_description": "Finish filling out the rest of the data in the sheet for SAMPLE PREP, LC PARAMETERS, "
                            "and MS PARAMETERS. If the data in a cell is not applicable or unknown, insert “N/A” or "
                            "“UNKNOWN” respectively. If your group has multiple values, insert “MULTIPLE” or a "
                            "Comma-Separated-Value. For Example, if you have multiple sexes in one group, you can add "
                            "“MULTIPLE” or “Male,Female”",
    },
    {
        "description": "Save and Upload .xlsm File",
        "long_description": "SAVE THE EDITS YOU HAVE MADE TO YOUR COMPUTER. Next, click “Choose File” and pick the "
                            ".xlsm file that you have been working on. Once you have selected, click “Upload Excel "
                            "File”",
    },
    {
        "description": "Review and Confirm",
        "long_description": "Look over the “Excel Upload Summary”. If everything is correct, click “confirm”. If you "
                            "need to make an edit, click “Cancel”, edit your .xlsm sheet, and re-upload the file. "
                            "NOTE - Some scientific terms might come up as “Typos” even though they aren’t typos. You "
                            "can ignore this. The → arrow suggest corrections, but will not change any data you have "
                            "inputted.",
    }
]


@login_required
def tutorial(request, step_number=1):
    if step_number < 1 or step_number > TOTAL_STEPS:
        return redirect("tutorial", step_number=1)

    step_info = TUTORIAL_STEPS[step_number - 1]
    step = {
        "number": step_number,
        "description": step_info["description"],
        "long_description": step_info["long_description"],
        "image": f"core/tutorial/tutorial-v-1-step-{step_number}.png",
    }

    return render(
        request,
        "core/tutorial.html",
        {
            "step": step,
            "total_steps": TOTAL_STEPS,
            "finish_redirect": FINISH_REDIRECT,
        },
    )
