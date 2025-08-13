from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),  # if you want to keep home
    path('register/', views.register, name='register'),
    path('projects/', views.project_list, name='project_list'),
    path('projects/new/', views.create_project, name='create_project'),
    path("start-project/", views.start_project, name="start_project"),
    path('upload-data/', views.upload_data, name='upload_data'),
]
