from datetime import datetime, date, timedelta
from django.db import transaction
from django.db.models import Sum, Count, Q
from django.shortcuts import get_object_or_404
import django_filters
from rest_framework import generics, status
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Timesheet
from projects.models import Project
from .serializers import (
    TimesheetSerializer,
    TimesheetListSerializer,
    TimesheetCreateSerializer,
    TimesheetDraftSerializer,
    TimesheetSummarySerializer,
    ValidateWeekTimesheetsSerializer,
    WeekSubmissionSerializer,
    BulkTimesheetActionSerializer,
    WeekSummarySerializer,
)

class TimesheetFilter(django_filters.FilterSet):
    date_from = django_filters.DateFilter(field_name="date", lookup_expr="gte")
    date_to   = django_filters.DateFilter(field_name="date", lookup_expr="lte")

    class Meta:
        model = Timesheet
        fields = ["project_id", "status", "activity_type", "date_from", "date_to"]

class TimesheetListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TimesheetListSerializer
    filterset_class = TimesheetFilter

    def get_queryset(self):
        return Timesheet.objects.filter(
            user=self.request.user
        ).select_related("project").order_by("-date", "-created_at")

    def create(self, request, *args, **kwargs):
        serializer = TimesheetCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            timesheet = serializer.save()
        return Response({
            "message": "Timesheet draft created successfully",
            "note": "Use weekly submission to submit all drafts at once",
            "timesheet": TimesheetSerializer(timesheet).data
        }, status=status.HTTP_201_CREATED)

class IsDraftEditableOrDeletable(BasePermission):
    """
    Allow editing/deleting only if timesheet is a draft.
    Submitting individually is blocked at serializer level.
    """

    def has_object_permission(self, request, view, obj):
        if request.method in ("PUT", "PATCH", "DELETE") and obj.status != "draft":
            return False
        return True

class TimesheetDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, IsDraftEditableOrDeletable]
    serializer_class = TimesheetSerializer

    def get_queryset(self):
        return Timesheet.objects.filter(user=self.request.user)
        
class MyTimesheetsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        today = date.today()
        date_from = request.GET.get('date_from') or (today - timedelta(days=today.weekday()))
        date_to = request.GET.get('date_to') or today

        timesheets = (Timesheet.objects
            .filter(user=request.user, date__range=[date_from, date_to])
            .select_related('project')
            .order_by('-date'))

        summary = {
            'total_hours': float(timesheets.aggregate(Sum('hours_worked'))['hours_worked__sum'] or 0),
            'total_entries': timesheets.count(),
            'draft_count': timesheets.filter(status='draft').count(),
            'submitted_count': timesheets.filter(status='submitted').count(),
            'date_range': f"{date_from} to {date_to}"
        }

        return Response({
            'timesheets': TimesheetListSerializer(timesheets, many=True).data,
            'summary': summary
        })
    
class DraftsListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
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

class SubmitWeekTimesheetsView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = WeekSubmissionSerializer(
            data=request.data, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        result = serializer.save()   
        return Response(result)

class WeekSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = WeekSummarySerializer(
            data=request.GET, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data)

class ValidateWeekTimesheetsView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ValidateWeekTimesheetsSerializer(
            data=request.data, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data)

class BulkTimesheetActionsView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = BulkTimesheetActionSerializer(
            data=request.data, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        return Response(serializer.save())

class TimesheetSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        date_from = request.GET.get("date_from", (date.today() - timedelta(days=30)))
        date_to = request.GET.get("date_to", date.today())

        serializer = TimesheetSummarySerializer.build(request.user, date_from, date_to)
        return Response(serializer.data)

class ProjectActivitiesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, project_id):
        """Get available activity types for a specific project"""
        project = get_object_or_404(Project, id=project_id)

        return Response({
            "project_id": project_id,
            "project_name": project.name,
            "activity_types": project.get_activity_types()
        })

class UserInfoView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get current user information for timesheets"""
        return Response({
            'user_id': request.user.id,
            'user_name': request.user.get_full_name(),
            'email': request.user.email,
            'designation': request.user.designation,
            'is_active': request.user.is_active,
            'is_admin': request.user.is_admin,
            'is_staff': request.user.is_staff
        })

class FindExistingTimesheetView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Get query parameters
        project_id = request.GET.get('project_id')
        activity_type = request.GET.get('activity_type')
        date_str = request.GET.get('date')

        # Validate parameters
        if not all([project_id, activity_type, date_str]):
            return Response({'error': 'Missing parameters: project_id, activity_type, date'}, status=400)

        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response({'error': 'Invalid date format. Use YYYY-MM-DD'}, status=400)

        # Check if timesheet exists
        timesheet = Timesheet.objects.filter(
            user=request.user,
            project_id=project_id,
            activity_type=activity_type,
            date=date_obj
        ).first()

        # Return response
        return Response({
            'exists': bool(timesheet),
            'timesheet': TimesheetSerializer(timesheet).data if timesheet else None,
            'message': f'Timesheet {"exists" if timesheet else "not found"} for project "{project_id}" '
                       f'with activity "{activity_type}" on {date_str}'
        })

class GetAllTimesheetsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not (request.user.is_staff or request.user.is_admin):
            return Response({"error": "Insufficient permissions", "message": "Admin privileges required"},
                            status=status.HTTP_403_FORBIDDEN)

        qs = Timesheet.objects.select_related("user", "project").order_by("-date", "-created_at")

        # Filters
        filters = {k: request.GET.get(k) for k in ["user_id", "project_id", "status", "activity_type",
                                                   "user_search", "project_search"]}
        if filters["user_id"]: qs = qs.filter(user_id=filters["user_id"])
        if filters["project_id"]: qs = qs.filter(project_id=filters["project_id"])
        if filters["status"]: qs = qs.filter(status=filters["status"])
        if filters["activity_type"]: qs = qs.filter(activity_type__icontains=filters["activity_type"])
        if filters["user_search"]:
            qs = qs.filter(Q(user__first_name__icontains=filters["user_search"]) |
                           Q(user__last_name__icontains=filters["user_search"]) |
                           Q(user__email__icontains=filters["user_search"]))
        if filters["project_search"]: qs = qs.filter(project__name__icontains=filters["project_search"])

        # Date filter
        today = date.today()
        date_from = request.GET.get("date_from", today.replace(day=1).strftime("%Y-%m-%d"))
        date_to = request.GET.get("date_to", today.strftime("%Y-%m-%d"))
        try:
            qs = qs.filter(date__gte=datetime.strptime(date_from, "%Y-%m-%d").date(),
                           date__lte=datetime.strptime(date_to, "%Y-%m-%d").date())
        except ValueError:
            return Response({"error": "Invalid date format (YYYY-MM-DD required)"}, status=400)

        # Pagination
        page_size = min(int(request.GET.get("page_size", 100)), 500)
        offset = int(request.GET.get("offset", 0))
        paginated = qs[offset:offset + page_size]
        serializer = TimesheetListSerializer(paginated, many=True)
        total_count = qs.count()

        # Aggregates
        agg = qs.aggregate(
            total_hours=Sum("hours_worked"),
            unique_users=Count("user", distinct=True),
            unique_projects=Count("project", distinct=True),
            draft_count=Count("id", filter=Q(status="draft")),
            submitted_count=Count("id", filter=Q(status="submitted"))
        )
        dashboard_stats = {
            "total_timesheets": total_count,
            "total_hours": float(agg["total_hours"] or 0),
            "unique_users": agg["unique_users"],
            "unique_projects": agg["unique_projects"],
            "draft_count": agg["draft_count"],
            "submitted_count": agg["submitted_count"],
            "date_range": f"{date_from} to {date_to}"
        }

        top_users = list(qs.values("user__first_name", "user__last_name", "user__email")
                         .annotate(total_hours=Sum("hours_worked"), entry_count=Count("id"))
                         .order_by("-total_hours")[:10])
        top_projects = list(qs.values("project__name")
                            .annotate(total_hours=Sum("hours_worked"), entry_count=Count("id"),
                                      unique_users=Count("user", distinct=True))
                            .order_by("-total_hours")[:10])

        return Response({
            "timesheets": serializer.data,
            "pagination": {"total_count": total_count, "page_size": page_size, "offset": offset,
                           "has_more": (offset + page_size) < total_count},
            "dashboard_stats": dashboard_stats,
            "top_users": top_users,
            "top_projects": top_projects,
            "filters_applied": {**filters, "date_from": date_from, "date_to": date_to},
        })
