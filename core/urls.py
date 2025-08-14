from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),  # Homepage
    path('register/', views.register, name='register'),

    # Project views
    path('projects/', views.project_list, name='project_list'),  # List of projects
    path('projects/new/', views.create_project, name='create_project'),  # Create project
    path('start-project/', views.start_project, name='start_project'),  # Generate/download Excel

    # Excel upload flow
    path('upload-preview/', views.upload_preview, name='upload_preview'),  # AJAX preview of uploaded Excel
    path('upload-project/', views.upload_project, name='upload_project'),  # AJAX save project + group data
]
