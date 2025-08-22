from rest_framework import serializers
from django.db.models import Sum
from datetime import date
from django.utils import timezone
from .models import Timesheet
from accounts.models import User
from projects.models import Project

class TimesheetSerializer(serializers.ModelSerializer):
    """Full serializer for detail views and create/update operations"""
    # Read-only fields for display
    user_name = serializers.ReadOnlyField()
    project_name = serializers.ReadOnlyField()
    user_email = serializers.CharField(source='user.email', read_only=True)
    can_edit = serializers.ReadOnlyField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    # For easier frontend handling
    project_activity_types = serializers.SerializerMethodField(read_only=True)
    daily_total_hours = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = Timesheet
        fields = [
            'id', 'user', 'user_email', 'user_name', 'project', 'project_name',
            'activity_type', 'date', 'hours_worked', 'description', 'status', 'status_display',
            'can_edit', 'project_activity_types', 'daily_total_hours',
            'created_at', 'updated_at', 'submitted_at'
        ]
        read_only_fields = [
            'id', 'user_name', 'project_name', 'can_edit', 'status_display', 
            'created_at', 'updated_at', 'submitted_at', 'status'
        ]
    
    def get_project_activity_types(self, obj):
        """Return available activity types for the project"""
        return obj.project.get_activity_types() if obj.project else []
    
    def get_daily_total_hours(self, obj):
        """Return total hours worked by user on this date"""
        return float(obj.total_hours_for_date)
    
    def validate(self, data):
        """Cross-field validation - prevent individual submission"""
        # Force status to remain draft for updates
        data['status'] = 'draft'
        return data

class TimesheetListSerializer(serializers.ModelSerializer):
    """Optimized serializer for list views - minimal fields"""
    user_name = serializers.ReadOnlyField()
    project_name = serializers.ReadOnlyField()
    user_email = serializers.CharField(source='user.email', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    can_edit = serializers.ReadOnlyField()
    
    class Meta:
        model = Timesheet
        fields = [
            'id', 'user_email', 'user_name', 'project_name',
            'activity_type', 'date', 'hours_worked', 'description',
            'status', 'status_display', 'can_edit', 'created_at', 'submitted_at'
        ]

class TimesheetCreateSerializer(serializers.ModelSerializer):
    """Serializer for timesheet creation - ALWAYS creates drafts only"""
    
    class Meta:
        model = Timesheet
        fields = [
            'project', 'activity_type', 'date', 'hours_worked', 'description'
        ]
    
    def validate(self, data):
        """Cross-field validation and permission checks"""
        request = self.context.get('request')
        
        # Set user to current logged-in user
        if request and request.user.is_authenticated:
            data['user'] = request.user
        else:
            raise serializers.ValidationError("Authentication required.")
        
        # FORCE status to be draft
        data['status'] = 'draft'
        
        # Relaxed validation for drafts - only basic checks
        project = data.get('project')
        if project and project.status != 'active':
            raise serializers.ValidationError("Cannot create timesheet for inactive project.")
        
        user = data['user']
        if not user.is_active:
            raise serializers.ValidationError("Cannot create timesheet for inactive user.")
        
        return data

class TimesheetDraftSerializer(serializers.ModelSerializer):
    """Serializer specifically for draft operations"""
    user_name = serializers.ReadOnlyField()
    project_name = serializers.ReadOnlyField()
    
    class Meta:
        model = Timesheet
        fields = [
            'id', 'user_name', 'project_name', 'activity_type', 
            'date', 'hours_worked', 'description', 'created_at'
        ]

class WeekSubmissionSerializer(serializers.Serializer):
    """Serializer for submitting a week's worth of timesheets"""
    week_start_date = serializers.DateField(
        help_text="Monday of the week to submit (YYYY-MM-DD format)"
    )
    timesheet_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        help_text="Optional: Specific timesheet IDs to submit. If not provided, all drafts for the week will be submitted."
    )
    force_submit = serializers.BooleanField(
        default=False,
        help_text="Submit even if there are warnings (but not errors)"
    )
    
    def validate_week_start_date(self, value):
        """Ensure the date is a Monday"""
        if value.weekday() != 0:  # 0 = Monday
            raise serializers.ValidationError("Week start date must be a Monday")
        return value

class WeekSummarySerializer(serializers.Serializer):
    """Serializer for week summary data"""
    week_start_date = serializers.DateField()
    week_end_date = serializers.DateField()
    week_range = serializers.CharField()
    total_hours = serializers.DecimalField(max_digits=6, decimal_places=2)
    total_entries = serializers.IntegerField()
    unique_projects = serializers.IntegerField()
    unique_dates = serializers.IntegerField()
    draft_count = serializers.IntegerField()
    submitted_count = serializers.IntegerField()
    daily_totals = serializers.DictField()
    project_totals = serializers.DictField()
    timesheets = TimesheetListSerializer(many=True)

class BulkTimesheetActionSerializer(serializers.Serializer):
    """Serializer for bulk actions on multiple timesheets"""
    timesheet_ids = serializers.ListField(
        child=serializers.IntegerField(),
        help_text="List of timesheet IDs to perform action on"
    )
    action = serializers.ChoiceField(
        choices=['submit', 'delete', 'validate'],
        help_text="Action to perform on selected timesheets"
    )
    
    def validate_timesheet_ids(self, value):
        """Validate timesheet IDs exist"""
        if not value:
            raise serializers.ValidationError("At least one timesheet ID is required")
        
        from .models import Timesheet
        existing_count = Timesheet.objects.filter(id__in=value).count()
        
        if existing_count != len(value):
            raise serializers.ValidationError("One or more timesheet IDs not found")
        
        return value