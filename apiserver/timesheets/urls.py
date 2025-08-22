from django.urls import path
from . import views

urlpatterns = [
    # Basic CRUD operations
    path('', views.timesheet_list_create, name='timesheet-list-create'),
    path('<int:pk>/', views.timesheet_detail, name='timesheet-detail'),
    
    # User-specific endpoints
    path('my-timesheets/', views.my_timesheets, name='my-timesheets'),
    path('user-info/', views.user_info, name='user-info'),
    path('drafts/', views.drafts_list, name='drafts-list'),
    
    # BULK/WEEKLY submission (THE ONLY WAY TO SUBMIT)
    path('submit-week/', views.submit_week_timesheets, name='submit-week'),
    path('week-summary/', views.get_week_summary, name='week-summary'),
    path('validate-week/', views.validate_week_timesheets_view, name='validate-week'),
    path('bulk-actions/', views.bulk_timesheet_actions, name='bulk-actions'),
    
    # Analytics and summary
    path('summary/', views.timesheet_summary, name='timesheet-summary'),
    
    # Helper endpoints
    path('project/<int:project_id>/activities/', views.project_activities, name='project-activities'),
]