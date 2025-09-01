from django.urls import path
from .views import ProjectListCreateView, ProjectDetailView, ProjectChoicesView, ActiveProjectsListView

urlpatterns = [
    path('', ProjectListCreateView.as_view(), name='project-list-create'),
    path('<int:pk>/', ProjectDetailView.as_view(), name='project-detail'),
    path('choices/', ProjectChoicesView.as_view(), name='project-choices'),
    path('active/', ActiveProjectsListView.as_view(), name='active-projects'),
]