from django.db import models
from django.contrib.auth.models import User


class ProjectData(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE)  # who created it
    project_name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    number_of_groups = models.PositiveIntegerField()
    group_names = models.TextField(help_text="Comma-separated group names")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.project_name
