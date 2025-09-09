from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),  # Homepage
    path('register/', views.register, name='register'),

    # Project views
    path("projects/", views.project_list, name="project_list"),
    path("create-project/", views.start_project, name="start_project"),
    path("upload-excel-preview/", views.upload_excel_preview, name="upload_excel_preview"),
    path("upload-excel-confirm/", views.upload_excel_confirm, name="upload_excel_confirm"),
    path("project/<int:project_id>/", views.project_detail, name="project_detail"),
    path("projects/<int:project_id>/subjects/", views.subject_data_page, name="subject_data"),
    path("project/<int:project_id>/add-subject-data/", views.add_subject_data, name="add_subject_data"),
    path("projects/<int:project_id>/subjects/<int:subject_id>/delete/", views.delete_subject, name="delete_subject"),
    path("project/<int:project_id>/files/", views.view_files, name="view_files"),
    path("project/<int:project_id>/file/<int:file_id>/delete/", views.delete_file, name="delete_file"),
    path("project/<int:project_id>/settings/", views.project_settings, name="project_settings"),
    path('project/<int:project_id>/join/<uuid:token>/', views.join_project, name='join_project'),
    path("project/<int:project_id>/about/", views.project_about, name="project_about"),
    path("project/<int:project_id>/raw-ms-data/", views.raw_ms_data, name="raw_ms_data"),
    path('tutorial/<int:step_number>/', views.tutorial, name='tutorial'),
]
