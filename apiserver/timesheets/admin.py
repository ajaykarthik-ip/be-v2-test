from django.contrib import admin
from django.db.models import Sum
from .models import Timesheet

@admin.register(Timesheet)
class TimesheetAdmin(admin.ModelAdmin):
    list_display = [
        'user_name', 'project_name', 'activity_type', 
        'date', 'hours_worked', 'description_preview', 'status', 'created_at'
    ]
    list_filter = [
        'date', 'activity_type', 'project__name', 'status',
        'user__designation', 'created_at'
    ]
    search_fields = [
        'user__first_name', 'user__last_name', 'user__email',
        'project__name', 'activity_type', 'description'
    ]
    ordering = ['-date', '-created_at']
    date_hierarchy = 'date'
    
    # Optimize queries
    list_select_related = ['user', 'project']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'project', 'activity_type', 'date', 'hours_worked')
        }),
        ('Details', {
            'fields': ('description', 'status')
        }),
        ('Metadata', {
            'fields': ('user_name', 'project_name', 'created_at', 'updated_at', 'submitted_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['user_name', 'project_name', 'created_at', 'updated_at', 'submitted_at']
    
    # Custom admin methods
    def description_preview(self, obj):
        """Show truncated description"""
        if obj.description:
            return obj.description[:50] + '...' if len(obj.description) > 50 else obj.description
        return '-'
    description_preview.short_description = 'Description'
    
    def get_queryset(self, request):
        """Optimize the queryset"""
        return super().get_queryset(request).select_related(
            'user', 'project'
        )
    
    # Add some custom actions
    actions = ['calculate_total_hours']
    
    def calculate_total_hours(self, request, queryset):
        """Calculate total hours for selected timesheets"""
        total = queryset.aggregate(total_hours=Sum('hours_worked'))['total_hours'] or 0
        self.message_user(request, f"Total hours for selected entries: {total}")
    calculate_total_hours.short_description = "Calculate total hours for selected entries"