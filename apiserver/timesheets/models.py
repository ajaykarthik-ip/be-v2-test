from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from datetime import date
from django.utils import timezone
from accounts.models import User
from projects.models import Project

class Timesheet(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
    ]
    
    # Link to User instead of separate Employee model
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='timesheets')
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='timesheets')
    activity_type = models.CharField(max_length=100)
    date = models.DateField()
    hours_worked = models.DecimalField(
        max_digits=5, 
        decimal_places=2,
        validators=[MinValueValidator(0.1), MaxValueValidator(24.0)]
    )
    description = models.TextField(blank=True, null=True)
    
    # Status field for draft functionality
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Denormalized fields for faster queries
    user_name = models.CharField(max_length=201, blank=True)  # full_name
    project_name = models.CharField(max_length=200, blank=True)
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-date', '-created_at']
        # Unique constraint - ensure one timesheet per user/project/date/activity combination regardless of status
        # This prevents confusion between draft and submitted activities with same name
        unique_together = ['user', 'project', 'date', 'activity_type']
        
        # Database indexes for performance
        indexes = [
            models.Index(fields=['user', 'date']),
            models.Index(fields=['project', 'date']),
            models.Index(fields=['date']),
            models.Index(fields=['user', 'project', 'date']),
            models.Index(fields=['-created_at']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.user_name} - {self.project_name} - {self.date} ({self.status})"
    
    def clean(self):
        """Model-level validation - only for submitted timesheets"""
        if self.status == 'submitted':
            # Check if date is not in the future
            if self.date and self.date > date.today():
                raise ValidationError('Date cannot be in the future.')
            
            # Validate activity type exists in project
            if self.project and self.activity_type:
                project_activities = self.project.get_activity_types()
                if project_activities and self.activity_type not in project_activities:
                    raise ValidationError(
                        f'Activity type "{self.activity_type}" is not valid for project "{self.project.name}". '
                        f'Valid activities: {", ".join(project_activities)}'
                    )
            
            # Check if user is active
            if self.user and not self.user.is_active:
                raise ValidationError('Cannot submit timesheet for inactive user.')
            
            # Check if project is active
            if self.project and self.project.status != 'active':
                raise ValidationError('Cannot submit timesheet for inactive project.')
    
    def save(self, *args, **kwargs):
        # Auto-populate denormalized fields
        if self.user:
            self.user_name = self.user.get_full_name()
        if self.project:
            self.project_name = self.project.name
        
        # Set submitted_at when status changes to submitted
        if self.status == 'submitted' and not self.submitted_at:
            self.submitted_at = timezone.now()
        
        # Only validate submitted timesheets
        if self.status == 'submitted':
            self.full_clean()
        
        super().save(*args, **kwargs)
    
    def submit(self):
        """Submit a draft timesheet"""
        if self.status == 'draft':
            self.status = 'submitted'
            self.submitted_at = timezone.now()
            self.save()
    
    @property
    def can_edit(self):
        """Check if timesheet can be edited"""
        return self.status == 'draft'
    
    @property
    def total_hours_for_date(self):
        """Get total hours worked by this user on this date"""
        return Timesheet.objects.filter(
            user=self.user,
            date=self.date
        ).aggregate(total=models.Sum('hours_worked'))['total'] or 0