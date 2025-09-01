from datetime import date, timedelta
from django.db.models import Sum, Count
from rest_framework import serializers
from django.db import transaction
from .utils import (
    get_week_start_end_dates,
    get_week_drafts,
    validate_week_timesheets,
    calculate_week_totals,
    format_week_range,
)
from .models import Timesheet

class TimesheetSerializer(serializers.ModelSerializer):
    """Full serializer for detail views and create/update operations"""
    user_name = serializers.ReadOnlyField()
    project_name = serializers.ReadOnlyField()
    user_email = serializers.CharField(source='user.email', read_only=True)
    can_edit = serializers.ReadOnlyField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    project_activity_types = serializers.SerializerMethodField()
    daily_total_hours = serializers.SerializerMethodField()
    
    class Meta:
        model = Timesheet
        fields = [
            'id', 'user', 'user_email', 'user_name', 'project', 'project_name',
            'activity_type', 'date', 'hours_worked', 'description', 'status', 'status_display',
            'can_edit', 'project_activity_types', 'daily_total_hours',
            'created_at', 'updated_at', 'submitted_at'
        ]
        read_only_fields = [
            'id', 'user', 'user_name', 'project_name', 'can_edit', 'status_display', 
            'created_at', 'updated_at', 'submitted_at'
        ]
    
    def get_project_activity_types(self, obj):
        return obj.project.get_activity_types() if obj.project else []
    
    def get_daily_total_hours(self, obj):
        return float(obj.total_hours_for_date)
    
    def validate(self, data):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return data

        # For updates, ensure only drafts can be edited and preserve draft status
        if self.instance:
            if self.instance.status != 'draft':
                raise serializers.ValidationError("Only draft timesheets can be edited.")
            if 'status' not in data:
                data['status'] = 'draft'
            data['user'] = self.instance.user
        else:
            data['status'] = 'draft'
            data['user'] = request.user

        project = data.get('project', getattr(self.instance, 'project', None))
        activity_type = data.get('activity_type', getattr(self.instance, 'activity_type', None))
        date = data.get('date', getattr(self.instance, 'date', None))

        if project and activity_type and date:
            qs = Timesheet.objects.filter(user=request.user, project=project, activity_type=activity_type, date=date)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                existing = qs.first()
                raise serializers.ValidationError({
                    'non_field_errors': [
                        f'A timesheet already exists for project "{project.name}" with activity "{activity_type}" on {date}. '
                        f'Update the existing entry (ID: {existing.id}) instead.'
                    ]
                })

        return data


class TimesheetListSerializer(serializers.ModelSerializer):
    user_name = serializers.ReadOnlyField()
    project_name = serializers.ReadOnlyField()
    user_email = serializers.CharField(source='user.email', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    can_edit = serializers.ReadOnlyField()

    class Meta:
        model = Timesheet
        fields = [
            "id", "user_email", "user_name", "project_name",
            "activity_type", "date", "hours_worked", "description",
            "status", "status_display", "can_edit",
            "created_at", "submitted_at"
        ]

class TimesheetCreateSerializer(serializers.ModelSerializer):
    """Serializer for timesheet creation - ALWAYS creates drafts only"""
    
    class Meta:
        model = Timesheet
        fields = [
            'project', 'activity_type', 'date', 'hours_worked', 'description'
        ]
    
    def validate(self, data):
        """Cross-field validation and permission checks with composite key uniqueness"""
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
        
        # Check for existing timesheet with same composite key
        activity_type = data.get('activity_type')
        date = data.get('date')
        
        if project and activity_type and date:
            from .models import Timesheet
            existing = Timesheet.objects.filter(
                user=user,
                project=project,
                activity_type=activity_type,
                date=date
            ).first()
            
            if existing:
                raise serializers.ValidationError({
                    'non_field_errors': [
                        f'A timesheet already exists for project "{project.name}" with activity "{activity_type}" on {date}. '
                        f'Please update the existing entry (ID: {existing.id}) instead of creating a new one.'
                    ]
                })
        
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
    week_start_date = serializers.DateField(help_text="Monday of the week (YYYY-MM-DD)")
    timesheet_ids = serializers.ListField(
        child=serializers.IntegerField(), required=False
    )
    force_submit = serializers.BooleanField(default=False)

    def validate_week_start_date(self, value):
        if value.weekday() != 0:
            raise serializers.ValidationError("Week start date must be a Monday")
        return value

    def save(self):
        user = self.context['request'].user
        week_start = self.validated_data['week_start_date']
        ids = self.validated_data.get('timesheet_ids')
        force = self.validated_data.get('force_submit', False)

        # Fetch timesheets
        if ids:
            start, end = get_week_start_end_dates(week_start)
            qs = Timesheet.objects.filter(
                id__in=ids, user=user, status='draft', date__range=[start, end]
            )
        else:
            qs = get_week_drafts(user, week_start)

        if not qs.exists():
            raise serializers.ValidationError({
                'error': 'No draft timesheets found',
                'week_range': format_week_range(week_start)
            })

        timesheets = list(qs.select_related('project', 'user'))
        validation = validate_week_timesheets(timesheets)

        if not validation['is_valid'] and not force:
            raise serializers.ValidationError({
                'error': 'Validation failed',
                'validation_errors': validation['timesheet_errors'],
                'week_warnings': validation['week_warnings']
            })

        with transaction.atomic():
            [t.submit() for t in timesheets]

        summary = calculate_week_totals(timesheets)
        return {
            'message': 'Week submitted successfully',
            'week_range': format_week_range(week_start),
            'submitted_count': len(timesheets),
            'total_hours': summary['total_hours'],
            'summary': summary,
            'submitted_timesheets': TimesheetListSerializer(timesheets, many=True).data
        }


class WeekSummarySerializer(serializers.Serializer):
    """Serializer for week summary data"""
    week_start = serializers.DateField(
        required=False,
        help_text="Monday of the week (YYYY-MM-DD). Defaults to current week."
    )

    def validate_week_start(self, value):
        if value and value.weekday() != 0:
            raise serializers.ValidationError("Week start date must be a Monday")
        return value

    def to_internal_value(self, data):
        validated = super().to_internal_value(data)
        if not validated.get("week_start"):
            today = date.today()
            validated["week_start"] = today - timedelta(days=today.weekday())
        return validated

    def to_representation(self, validated_data):
        user = self.context['request'].user
        week_start_date = validated_data['week_start']

        # Get boundaries
        week_start, week_end = get_week_start_end_dates(week_start_date)

        # Fetch timesheets
        timesheets = (Timesheet.objects
            .filter(user=user, date__range=[week_start, week_end])
            .select_related('project')
            .order_by('date', 'created_at'))

        totals = calculate_week_totals(timesheets)

        return {
            'week_start_date': week_start,
            'week_end_date': week_end,
            'week_range': format_week_range(week_start_date),
            'total_hours': totals['total_hours'],
            'total_entries': totals['total_entries'],
            'unique_projects': totals['unique_projects'],
            'unique_dates': totals['unique_dates'],
            'draft_count': timesheets.filter(status='draft').count(),
            'submitted_count': timesheets.filter(status='submitted').count(),
            'daily_totals': totals['daily_totals'],
            'project_totals': totals['project_totals'],
            'timesheets': TimesheetListSerializer(timesheets, many=True).data
        }


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
        if not value:
            raise serializers.ValidationError("At least one timesheet ID is required")
        return value

    def save(self):
        from .models import Timesheet
        user = self.context['request'].user
        ids = self.validated_data['timesheet_ids']
        action = self.validated_data['action']

        timesheets = Timesheet.objects.filter(id__in=ids, user=user)
        if timesheets.count() != len(ids):
            raise serializers.ValidationError("Some timesheets not found or do not belong to you")

        # === Submit ===
        if action == 'submit':
            drafts = timesheets.filter(status='draft')
            if not drafts.exists():
                raise serializers.ValidationError("No draft timesheets to submit")

            validation = validate_week_timesheets(list(drafts))
            if not validation['is_valid']:
                raise serializers.ValidationError({
                    'error': 'Validation failed',
                    'validation_errors': validation
                })

            with transaction.atomic():
                for t in drafts:
                    t.submit()

            return {
                'message': f'Successfully submitted {drafts.count()} timesheets',
                'submitted_count': drafts.count()
            }

        # === Delete ===
        if action == 'delete':
            drafts = timesheets.filter(status='draft')
            if not drafts.exists():
                raise serializers.ValidationError("No draft timesheets to delete")
            count = drafts.count()
            drafts.delete()
            return {
                'message': f'Successfully deleted {count} draft timesheets',
                'deleted_count': count
            }

        # === Validate ===
        if action == 'validate':
            validation = validate_week_timesheets(list(timesheets))
            return {
                'message': 'Validation completed',
                'validation_result': validation
            }

    

class ValidateWeekTimesheetsSerializer(serializers.Serializer):
    week_start_date = serializers.DateField(help_text="Monday of the week (YYYY-MM-DD)")

    def validate_week_start_date(self, value):
        if value.weekday() != 0:
            raise serializers.ValidationError("Week start date must be a Monday")
        return value

    def to_representation(self, validated_data):
        user = self.context['request'].user
        week_start_date = validated_data['week_start_date']

        # Fetch draft timesheets
        drafts = get_week_drafts(user, week_start_date)

        if not drafts.exists():
            return {
                'message': 'No draft timesheets found for validation',
                'week_range': format_week_range(week_start_date),
                'is_valid': True,
                'has_warnings': False
            }

        validation = validate_week_timesheets(list(drafts))

        return {
            'week_range': format_week_range(week_start_date),
            'validation_result': validation,
            'timesheets_checked': drafts.count()
        }

class TimesheetSummarySerializer(serializers.Serializer):
    date_from = serializers.DateField()
    date_to = serializers.DateField()
    daily_summary = serializers.ListField()
    project_summary = serializers.ListField()
    activity_summary = serializers.ListField()

    @classmethod
    def build(cls, user, date_from, date_to):
        qs = Timesheet.objects.filter(user=user, date__gte=date_from, date__lte=date_to)

        return cls({
            "date_from": date_from,
            "date_to": date_to,
            "daily_summary": list(
                qs.values("date").annotate(
                    total_hours=Sum("hours_worked"),
                    project_count=Count("project", distinct=True)
                ).order_by("date")
            ),
            "project_summary": list(
                qs.values("project__name").annotate(
                    total_hours=Sum("hours_worked"),
                    entry_count=Count("id")
                ).order_by("-total_hours")
            ),
            "activity_summary": list(
                qs.values("activity_type").annotate(
                    total_hours=Sum("hours_worked"),
                    entry_count=Count("id")
                ).order_by("-total_hours")
            ),
        })
