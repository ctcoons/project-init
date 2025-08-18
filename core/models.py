from django.contrib.auth.models import User
from django.db import models
from django.conf import settings


class ProjectData(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    project_name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    number_of_groups = models.PositiveIntegerField()
    group_names = models.TextField(help_text="Comma-separated group names")
    independent_variable = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)  # <- this is correct  # Comma-separated group names

    def __str__(self):
        return f"{self.project_name} ({self.owner.username})"


class GroupData(models.Model):
    project = models.ForeignKey(ProjectData, on_delete=models.CASCADE, related_name="group_data")
    group_name = models.CharField(max_length=200)


class GroupSubData(models.Model):
    group = models.ForeignKey(GroupData, on_delete=models.CASCADE, related_name="group_sub_data")
    category = models.CharField(max_length=200)
    label = models.TextField()
    value = models.TextField(null=True)


# models.py
class Subject(models.Model):
    group = models.ForeignKey(GroupData, related_name="subjects", on_delete=models.CASCADE)
    metadata = models.JSONField(default=dict, blank=True)  # store CSV row
