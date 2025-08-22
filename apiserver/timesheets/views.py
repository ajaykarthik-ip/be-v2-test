from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import Sum, Count, Q
from datetime import datetime, date, timedelta
from .models import Timesheet
from .serializers import (
    TimesheetSerializer, TimesheetListSerializer, 
    TimesheetCreateSerializer, TimesheetDraftSerializer,
    WeekSubmissionSerializer, WeekSummarySerializer, 
    BulkTimesheetActionSerializer
)
from projects.models import Project
from .utils import (
    get_week_start_end_dates, get_week_drafts, 
    calculate_week_totals, validate_week_timesheets, format_week_range
)

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def timesheet_list_create(request):
    """
    GET: List user's timesheets with filtering
    POST: Create new timesheet (ALWAYS as draft)
    """
    if request.method == 'GET':
        # Get current user's timesheets only
        timesheets = Timesheet.objects.filter(
            user=request.user
        ).select_related('project').order_by('-date', '-created_at')
        
        # Filtering
        project_id = request.GET.get('project_id')
        if project_id:
            timesheets = timesheets.filter(project_id=project_id)
        
        # Status filtering
        status_filter = request.GET.get('status')
        if status_filter:
            timesheets = timesheets.filter(status=status_filter)
        
        # Date filtering
        date_from = request.GET.get('date_from')
        date_to = request.GET.get('date_to')
        
        # Default to current month if no dates provided
        if not date_from and not date_to:
            today = date.today()
            date_from = today.replace(day=1).strftime('%Y-%m-%d')
            date_to = today.strftime('%Y-%m-%d')
        
        if date_from:
            try:
                date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
                timesheets = timesheets.filter(date__gte=date_from_obj)
            except ValueError:
                return Response({'error': 'Invalid date_from format. Use YYYY-MM-DD'}, status=400)
        
        if date_to:
            try:
                date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
                timesheets = timesheets.filter(date__lte=date_to_obj)
            except ValueError:
                return Response({'error': 'Invalid date_to format. Use YYYY-MM-DD'}, status=400)
        
        # Activity type filtering
        activity_type = request.GET.get('activity_type')
        if activity_type:
            timesheets = timesheets.filter(activity_type__icontains=activity_type)
        
        # Pagination
        page_size = min(int(request.GET.get('page_size', 50)), 100)
        
        serializer = TimesheetListSerializer(timesheets[:page_size], many=True)
        
        return Response({
            'count': timesheets.count(),
            'timesheets': serializer.data,
            'filters_applied': {
                'date_from': date_from,
                'date_to': date_to,
                'project_id': project_id,
                'activity_type': activity_type,
                'status': status_filter
            }
        })
    
    elif request.method == 'POST':
        serializer = TimesheetCreateSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    timesheet = serializer.save()
                return Response({
                    'message': 'Timesheet draft created successfully',
                    'note': 'Use weekly submission to submit all drafts at once',
                    'timesheet': TimesheetSerializer(timesheet).data
                }, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response({
                    'error': 'Failed to create timesheet',
                    'details': str(e)
                }, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def timesheet_detail(request, pk):
    """
    GET: Retrieve timesheet by ID
    PUT: Update timesheet (but prevent individual submission)
    DELETE: Delete timesheet (only drafts)
    """
    try:
        timesheet = Timesheet.objects.get(pk=pk, user=request.user)
    except Timesheet.DoesNotExist:
        return Response({'error': 'Timesheet not found'}, status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'GET':
        serializer = TimesheetSerializer(timesheet)
        return Response({
            'timesheet': serializer.data
        })
    
    elif request.method == 'PUT':
        # Only allow editing of drafts
        if timesheet.status != 'draft':
            return Response({
                'error': 'Cannot edit submitted timesheet',
                'message': 'Only draft timesheets can be modified'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # PREVENT individual submission through update
        if request.data.get('status') == 'submitted':
            return Response({
                'error': 'Individual submission not allowed',
                'message': 'Use weekly bulk submission instead'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = TimesheetSerializer(timesheet, data=request.data, partial=True)
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    timesheet = serializer.save()
                return Response({
                    'message': 'Timesheet draft updated successfully',
                    'timesheet': TimesheetSerializer(timesheet).data
                })
            except Exception as e:
                return Response({
                    'error': 'Failed to update timesheet',
                    'details': str(e)
                }, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        # Only allow deletion of drafts
        if timesheet.status == 'submitted':
            return Response({
                'error': 'Cannot delete submitted timesheet'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            with transaction.atomic():
                timesheet.delete()
            return Response({
                'message': 'Timesheet draft deleted successfully'
            }, status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({
                'error': 'Failed to delete timesheet',
                'details': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_timesheets(request):
    """Get current user's timesheets with summary"""
    # Date filtering with defaults
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if not date_from:
        # Default to current week
        today = date.today()
        start_of_week = today - timedelta(days=today.weekday())
        date_from = start_of_week.strftime('%Y-%m-%d')
    
    if not date_to:
        date_to = date.today().strftime('%Y-%m-%d')
    
    timesheets = Timesheet.objects.filter(
        user=request.user,
        date__gte=date_from,
        date__lte=date_to
    ).select_related('project').order_by('-date')
    
    serializer = TimesheetListSerializer(timesheets, many=True)
    
    # Calculate summary
    total_hours = timesheets.aggregate(total=Sum('hours_worked'))['total'] or 0
    draft_count = timesheets.filter(status='draft').count()
    submitted_count = timesheets.filter(status='submitted').count()
    
    return Response({
        'timesheets': serializer.data,
        'summary': {
            'total_hours': float(total_hours),
            'total_entries': timesheets.count(),
            'draft_count': draft_count,
            'submitted_count': submitted_count,
            'date_range': f"{date_from} to {date_to}"
        }
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def drafts_list(request):
    """Get current user's draft timesheets"""
    drafts = Timesheet.objects.filter(
        user=request.user,
        status='draft'
    ).select_related('project').order_by('-created_at')
    
    serializer = TimesheetDraftSerializer(drafts, many=True)
    
    return Response({
        'drafts': serializer.data,
        'total_drafts': drafts.count()
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_week_timesheets(request):
    """
    Submit all draft timesheets for a specific week
    """
    serializer = WeekSubmissionSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response({
            'error': 'Invalid request data',
            'details': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    week_start_date = serializer.validated_data['week_start_date']
    specific_ids = serializer.validated_data.get('timesheet_ids')
    force_submit = serializer.validated_data.get('force_submit', False)
    
    # Get timesheets to submit
    if specific_ids:
        week_start, week_end = get_week_start_end_dates(week_start_date)
        timesheets_to_submit = Timesheet.objects.filter(
            id__in=specific_ids,
            user=request.user,
            status='draft',
            date__gte=week_start,
            date__lte=week_end
        ).select_related('project', 'user')
    else:
        timesheets_to_submit = get_week_drafts(request.user, week_start_date)
    
    if not timesheets_to_submit.exists():
        return Response({
            'error': 'No draft timesheets found for the specified week',
            'week_range': format_week_range(week_start_date)
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Convert to list for validation
    timesheet_list = list(timesheets_to_submit)
    
    # Validate all timesheets before submission
    validation_result = validate_week_timesheets(timesheet_list)
    
    if not validation_result['is_valid']:
        return Response({
            'error': 'Week submission failed validation',
            'validation_errors': validation_result['timesheet_errors'],
            'week_warnings': validation_result['week_warnings']
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Perform the bulk submission
    submitted_timesheets = []
    
    try:
        with transaction.atomic():
            for timesheet in timesheet_list:
                timesheet.submit()
                submitted_timesheets.append(timesheet)
    except Exception as e:
        return Response({
            'error': 'Week submission failed',
            'details': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Calculate summary for response
    summary = calculate_week_totals(submitted_timesheets)
    
    return Response({
        'message': 'Week submitted successfully',
        'week_range': format_week_range(week_start_date),
        'submitted_count': len(submitted_timesheets),
        'total_hours': summary['total_hours'],
        'summary': summary,
        'submitted_timesheets': TimesheetListSerializer(submitted_timesheets, many=True).data
    }, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_week_summary(request):
    """
    Get summary of timesheets for a specific week
    """
    # Get week_start parameter
    week_start_param = request.GET.get('week_start')
    if not week_start_param:
        # Default to current week
        today = date.today()
        week_start_date = today - timedelta(days=today.weekday())
    else:
        try:
            week_start_date = datetime.strptime(week_start_param, '%Y-%m-%d').date()
        except ValueError:
            return Response({'error': 'Invalid week_start format. Use YYYY-MM-DD'}, status=400)
    
    # Get week boundaries
    week_start, week_end = get_week_start_end_dates(week_start_date)
    
    # Get all timesheets for the week (both draft and submitted)
    week_timesheets = Timesheet.objects.filter(
        user=request.user,
        date__gte=week_start,
        date__lte=week_end
    ).select_related('project').order_by('date', 'created_at')
    
    # Separate drafts and submitted
    draft_timesheets = week_timesheets.filter(status='draft')
    submitted_timesheets = week_timesheets.filter(status='submitted')
    
    # Calculate totals
    week_totals = calculate_week_totals(week_timesheets)
    
    # Prepare response data
    response_data = {
        'week_start_date': week_start,
        'week_end_date': week_end,
        'week_range': format_week_range(week_start_date),
        'total_hours': week_totals['total_hours'],
        'total_entries': week_totals['total_entries'],
        'unique_projects': week_totals['unique_projects'],
        'unique_dates': week_totals['unique_dates'],
        'draft_count': draft_timesheets.count(),
        'submitted_count': submitted_timesheets.count(),
        'daily_totals': week_totals['daily_totals'],
        'project_totals': week_totals['project_totals'],
        'timesheets': TimesheetListSerializer(week_timesheets, many=True).data
    }
    
    return Response(response_data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def validate_week_timesheets_view(request):
    """
    Validate draft timesheets for a specific week without submitting
    """
    week_start_date = request.data.get('week_start_date')
    
    if not week_start_date:
        return Response({'error': 'week_start_date is required'}, status=400)
    
    try:
        week_start_date = datetime.strptime(week_start_date, '%Y-%m-%d').date()
    except ValueError:
        return Response({'error': 'Invalid date format. Use YYYY-MM-DD'}, status=400)
    
    # Get draft timesheets for the week
    draft_timesheets = get_week_drafts(request.user, week_start_date)
    
    if not draft_timesheets.exists():
        return Response({
            'message': 'No draft timesheets found for validation',
            'week_range': format_week_range(week_start_date),
            'is_valid': True,
            'has_warnings': False
        })
    
    # Validate the timesheets
    validation_result = validate_week_timesheets(list(draft_timesheets))
    
    return Response({
        'week_range': format_week_range(week_start_date),
        'validation_result': validation_result,
        'timesheets_checked': draft_timesheets.count()
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def bulk_timesheet_actions(request):
    """
    Perform bulk actions on multiple timesheets
    """
    serializer = BulkTimesheetActionSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=400)
    
    timesheet_ids = serializer.validated_data['timesheet_ids']
    action = serializer.validated_data['action']
    
    # Get timesheets (ensure they belong to the user)
    timesheets = Timesheet.objects.filter(
        id__in=timesheet_ids,
        user=request.user
    )
    
    if timesheets.count() != len(timesheet_ids):
        return Response({
            'error': 'Some timesheets not found or do not belong to you'
        }, status=404)
    
    # Perform the requested action
    if action == 'submit':
        # Submit selected timesheets
        draft_timesheets = timesheets.filter(status='draft')
        
        if not draft_timesheets.exists():
            return Response({'error': 'No draft timesheets to submit'}, status=400)
        
        # Validate before submitting
        validation_result = validate_week_timesheets(list(draft_timesheets))
        if not validation_result['is_valid']:
            return Response({
                'error': 'Validation failed',
                'validation_errors': validation_result
            }, status=400)
        
        # Submit all
        submitted_count = 0
        with transaction.atomic():
            for timesheet in draft_timesheets:
                timesheet.submit()
                submitted_count += 1
        
        return Response({
            'message': f'Successfully submitted {submitted_count} timesheets',
            'submitted_count': submitted_count
        })
    
    elif action == 'delete':
        # Delete selected timesheets (only drafts)
        draft_timesheets = timesheets.filter(status='draft')
        
        if not draft_timesheets.exists():
            return Response({'error': 'No draft timesheets to delete'}, status=400)
        
        deleted_count = draft_timesheets.count()
        draft_timesheets.delete()
        
        return Response({
            'message': f'Successfully deleted {deleted_count} draft timesheets',
            'deleted_count': deleted_count
        })
    
    elif action == 'validate':
        # Validate selected timesheets
        validation_result = validate_week_timesheets(list(timesheets))
        
        return Response({
            'message': 'Validation completed',
            'validation_result': validation_result
        })
    
    else:
        return Response({'error': 'Invalid action'}, status=400)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def timesheet_summary(request):
    """Get timesheet summary/analytics for current user"""
    # Date filtering
    date_from = request.GET.get('date_from', (date.today() - timedelta(days=30)).strftime('%Y-%m-%d'))
    date_to = request.GET.get('date_to', date.today().strftime('%Y-%m-%d'))
    
    # Daily summary
    daily_summary = Timesheet.objects.filter(
        user=request.user,
        date__gte=date_from,
        date__lte=date_to
    ).values('date').annotate(
        total_hours=Sum('hours_worked'),
        project_count=Count('project', distinct=True)
    ).order_by('date')
    
    # Project summary
    project_summary = Timesheet.objects.filter(
        user=request.user,
        date__gte=date_from,
        date__lte=date_to
    ).values('project__name').annotate(
        total_hours=Sum('hours_worked'),
        entry_count=Count('id')
    ).order_by('-total_hours')
    
    # Activity summary
    activity_summary = Timesheet.objects.filter(
        user=request.user,
        date__gte=date_from,
        date__lte=date_to
    ).values('activity_type').annotate(
        total_hours=Sum('hours_worked'),
        entry_count=Count('id')
    ).order_by('-total_hours')
    
    return Response({
        'daily_summary': list(daily_summary),
        'project_summary': list(project_summary),
        'activity_summary': list(activity_summary),
        'date_range': f"{date_from} to {date_to}"
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def project_activities(request, project_id):
    """Get available activity types for a specific project"""
    try:
        project = Project.objects.get(id=project_id)
        return Response({
            'project_id': project_id,
            'project_name': project.name,
            'activity_types': project.get_activity_types()
        })
    except Project.DoesNotExist:
        return Response({'error': 'Project not found'}, status=404)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_info(request):
    """Get current user information for timesheets"""
    return Response({
        'user_id': request.user.id,
        'user_name': request.user.get_full_name(),
        'email': request.user.email,
        'designation': request.user.get_designation_based_on_admin(),
        'company': getattr(request.user, 'company', 'Mobiux'),
        'is_active': request.user.is_active
    })