from django.urls import path
from .views import BulkTimesheetActionsView, DraftsListView, FindExistingTimesheetView, GetAllTimesheetsView, MyTimesheetsView, ProjectActivitiesView, SubmitWeekTimesheetsView, TimesheetDetailView, TimesheetListCreateView, TimesheetSummaryView, UserInfoView, ValidateWeekTimesheetsView, WeekSummaryView

urlpatterns = [
    # Basic CRUD operations
    # path('', views.timesheet_list_create, name='timesheet-list-create'),
    path('', TimesheetListCreateView.as_view(), name='timesheet-list-create'),

    # path('<int:pk>/', views.timesheet_detail, name='timesheet-detail'),
    path('<int:pk>/', TimesheetDetailView.as_view(), name='timesheet-detail'),

    
    # User-specific endpoints
    # path('my-timesheets/', views.my_timesheets, name='my-timesheets'),
    path('my-timesheets/', MyTimesheetsView.as_view(), name='my-timesheets'),

    # path('user-info/', views.user_info, name='user-info'),
    path('user-info/', UserInfoView.as_view(), name="user-info"),

    # path('drafts/', views.drafts_list, name='drafts-list'),
    path('drafts/', DraftsListView.as_view(), name='drafts-list'),

    
    # BULK/WEEKLY submission (THE ONLY WAY TO SUBMIT)

    # path('submit-week/', views.submit_week_timesheets, name='submit-week'),
    path('submit-week/', SubmitWeekTimesheetsView.as_view(), name='submit-week'),

    # path('week-summary/', views.get_week_summary, name='week-summary'),
    path('week-summary/', WeekSummaryView.as_view(), name='week-summary'),

    # path('validate-week/', views.validate_week_timesheets_view, name='validate-week'),
    path('validate-week/', ValidateWeekTimesheetsView.as_view(), name='validate-week'),

    # path('bulk-actions/', views.bulk_timesheet_actions, name='bulk-actions'),
    path('bulk-actions/', BulkTimesheetActionsView.as_view(), name='bulk-actions'),


    
    # Analytics and summary

    # path('summary/', views.timesheet_summary, name='timesheet-summary'),
    path('summary/', TimesheetSummaryView.as_view(), name='timesheet-summary'),

    
    # Helper endpoints

    # path('project/<int:project_id>/activities/', views.project_activities, name='project-activities'),
    path("project/<int:project_id>/activities/", ProjectActivitiesView.as_view(), name="project-activities"),

    # path('find-existing/', views.find_existing_timesheet, name='find-existing-timesheet'),
    path('find-existing/', FindExistingTimesheetView.as_view(), name="find-existing-timesheet"),


    # path('all/', views.get_all_timesheets, name='get-all-timesheets'),
    path('all/', GetAllTimesheetsView.as_view(), name="get-all-timesheets"),
    # path("all/", get_all_timesheets, name="all-timesheets"),


]