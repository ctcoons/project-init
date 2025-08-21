import uuid
from importlib.metadata import metadata

from django.contrib.auth.models import User
from django.db import models


class ProjectData(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="owned_projects")
    project_name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    number_of_groups = models.PositiveIntegerField()
    group_names = models.TextField(help_text="Tab-separated group names")
    independent_variable = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_owner(self, user):
        return self.owner == user

    def get_role(self, user):
        """Return 'owner', 'collaborator', or None if no membership."""
        if self.is_owner(user):
            return "owner"
        membership = self.memberships.filter(user=user).first()
        return membership.role if membership else None

    def can_edit(self, user):
        """Owner and collaborators can edit; everyone can view."""
        return self.get_role(user) in ["owner", "collaborator"]

    def __str__(self):
        return f"{self.project_name} ({self.owner.username})"


class ProjectMembership(models.Model):
    ROLE_CHOICES = [
        ("owner", "Owner"),
        ("collaborator", "Collaborator"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    project = models.ForeignKey(ProjectData, on_delete=models.CASCADE, related_name="memberships")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="collaborator")

    class Meta:
        unique_together = ("user", "project")  # prevent duplicates

    def __str__(self):
        return f"{self.user.username} - {self.project.project_name} ({self.role})"


class GroupData(models.Model):
    project = models.ForeignKey(ProjectData, on_delete=models.CASCADE, related_name="group_data")
    group_name = models.CharField(max_length=200)

    def __str__(self):
        return f"{self.group_name}"


class GroupSubData(models.Model):
    group = models.ForeignKey(GroupData, on_delete=models.CASCADE, related_name="group_sub_data")
    category = models.CharField(max_length=200)
    label = models.TextField()
    value = models.TextField(null=True)


class Subject(models.Model):
    group = models.ForeignKey(GroupData, related_name="subjects", on_delete=models.CASCADE)
    metadata = models.JSONField(default=dict, blank=True)  # store CSV row

    def __str__(self):
        return f"Subject: {str(self.metadata)}, Group: {str(self.group)}"


class ProjectFile(models.Model):
    VISIBILITY_CHOICES = [
        ("private", "Private"),
        ("public", "Public"),
    ]

    project = models.ForeignKey(ProjectData, on_delete=models.CASCADE, related_name="files")
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)
    file = models.FileField(upload_to="project_files/")
    visibility = models.CharField(max_length=10, choices=VISIBILITY_CHOICES, default="private")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.file.name} ({self.visibility})"


class ProjectJoinToken(models.Model):
    project = models.ForeignKey(ProjectData, on_delete=models.CASCADE, related_name="join_tokens")
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.project.project_name} - {self.token}"