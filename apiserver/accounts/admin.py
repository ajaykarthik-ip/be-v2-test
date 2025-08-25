# apiserver/accounts/admin.py
from django.contrib import admin
from .models import User

class UserAdmin(admin.ModelAdmin):
    """Custom admin for User model without Django's default user admin inheritance"""
    
    # Display settings
    list_display = ['email', 'first_name', 'last_name', 'designation', 'company', 'active', 'staff', 'admin', 'last_login']
    list_filter = ['active', 'staff', 'admin', 'designation', 'company', 'last_login']
    search_fields = ['email', 'first_name', 'last_name']
    ordering = ['email']
    
    # Form layout for editing existing users
    fieldsets = (
        ('Authentication', {
            'fields': ('email', 'password')
        }),
        ('Personal Information', {
            'fields': ('first_name', 'last_name', 'designation', 'company')
        }),
        ('Permissions', {
            'fields': ('active', 'staff', 'admin'),
            'description': 'Admin = Superuser with all permissions, Staff = Can access admin panel'
        }),
        ('Important Dates', {
            'fields': ('last_login',),
            'classes': ('collapse',)
        }),
    )
    
    # Form layout for adding new users
    add_fieldsets = (
        ('Create New User', {
            'classes': ('wide',),
            'fields': ('email', 'password', 'first_name', 'last_name', 'designation', 'company', 'active', 'staff', 'admin'),
        }),
    )
    
    readonly_fields = ['last_login']
    
    # Custom admin actions
    actions = ['make_admin', 'remove_admin', 'activate_users', 'deactivate_users']
    
    def make_admin(self, request, queryset):
        """Make selected users admin"""
        updated = queryset.update(admin=True, staff=True)
        self.message_user(request, f'{updated} users were successfully promoted to admin.')
    make_admin.short_description = "✅ Promote selected users to admin"
    
    def remove_admin(self, request, queryset):
        """Remove admin privileges from selected users"""
        updated = queryset.update(admin=False)
        self.message_user(request, f'{updated} users had admin privileges removed.')
    remove_admin.short_description = "❌ Remove admin privileges from selected users"
    
    def activate_users(self, request, queryset):
        """Activate selected users"""
        updated = queryset.update(active=True)
        self.message_user(request, f'{updated} users were successfully activated.')
    activate_users.short_description = "🟢 Activate selected users"
    
    def deactivate_users(self, request, queryset):
        """Deactivate selected users"""
        updated = queryset.update(active=False)
        self.message_user(request, f'{updated} users were successfully deactivated.')
    deactivate_users.short_description = "🔴 Deactivate selected users"
    
    def get_fieldsets(self, request, obj=None):
        """Use add_fieldsets when adding a new user"""
        if not obj:
            return self.add_fieldsets
        return super().get_fieldsets(request, obj)

# Register the User model with our custom admin
admin.site.register(User, UserAdmin)