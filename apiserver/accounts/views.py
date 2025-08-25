
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import User


@api_view(['GET'])
@permission_classes([AllowAny])
def test_endpoint(request):
    return Response({'message': 'Test endpoint working'})


@api_view(['POST'])
@permission_classes([AllowAny])
def register_user(request):
    """User registration endpoint"""
    try:
        print("DEBUG: Request received")
        
        email = request.data.get('email')
        password = request.data.get('password')
        first_name = request.data.get('first_name', '')
        last_name = request.data.get('last_name', '')
        designation = request.data.get('designation', 'employee')  # Default to 'employee'
        
        print(f"DEBUG: Data received - email: {email}")
        
        # Validation
        if not email or not password:
            return Response({
                'error': 'Email and password are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if user already exists
        if User.objects.filter(email=email).exists():
            return Response({
                'error': 'User with this email already exists'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create user
        user = User.objects.create_user(
            email=email,
            password=password
        )
        
        # Set additional fields
        user.first_name = first_name
        user.last_name = last_name
        user.designation = designation
        user.company = "Mobiux"  # Default company
        user.save()
        
        print(f"DEBUG: User created successfully - ID: {user.id}")
        
        return Response({
            'message': 'User created successfully',
            'user': {
                'id': user.id,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'designation': user.get_designation_based_on_admin(),
                'company': user.company,
                'role': user.get_role_display()
            }
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        print(f"DEBUG: Exception: {str(e)}")
        import traceback
        traceback.print_exc()
        return Response({
            'error': f'Internal server error: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def user_profile(request):

    user = request.user
    
    if request.method == 'GET':
        return Response({
            'user': {
                'id': user.id,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'is_active': user.is_active,
                'is_staff': user.is_staff,
                'is_admin': user.is_admin,
                'last_login': user.last_login,
                'full_name': user.get_full_name(),
                'designation': user.get_designation_based_on_admin(),  
                'company': user.company,
                'role': user.get_role_display() 
            }
        }, status=status.HTTP_200_OK)
    
    elif request.method == 'PUT':
        # Update user profile
        try:
            # Allow updating certain fields
            allowed_fields = ['first_name', 'last_name', 'designation']
            
            for field in allowed_fields:
                if field in request.data:
                    setattr(user, field, request.data[field])
            
            user.save()
            
            return Response({
                'message': 'Profile updated successfully',
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'is_active': user.is_active,
                    'is_staff': user.is_staff,
                    'is_admin': user.is_admin,
                    'last_login': user.last_login,
                    'full_name': user.get_full_name(),
                    'designation': user.get_designation_based_on_admin(),
                    'company': user.company,
                    'role': user.get_role_display()
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': f'Failed to update profile: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def change_password(request):
    """Change user password"""
    user = request.user
    
    old_password = request.data.get('old_password')
    new_password = request.data.get('new_password')
    
    if not old_password or not new_password:
        return Response({
            'error': 'Both old_password and new_password are required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Verify old password
    if not user.check_password(old_password):
        return Response({
            'error': 'Current password is incorrect'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Set new password
    user.set_password(new_password)
    user.save()
    
    return Response({
        'message': 'Password changed successfully'
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def login_user(request):
    """User login endpoint"""
    email = request.data.get('email')
    password = request.data.get('password')
    
    if not email or not password:
        return Response({
            'error': 'Email and password are required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        user = User.objects.get(email=email)
        if user.check_password(password):
            from rest_framework_simplejwt.tokens import RefreshToken
            refresh = RefreshToken.for_user(user)
            
            return Response({
                'message': 'Login successful',
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'full_name': user.get_full_name(),
                    'designation': user.get_designation_based_on_admin(),
                    'company': getattr(user, 'company', 'Mobiux'),
                    'is_active': user.is_active,
                    'is_staff': user.is_staff,
                    'is_admin': user.is_admin,
                }
            })
        else:
            return Response({
                'error': 'Invalid credentials'
            }, status=status.HTTP_401_UNAUTHORIZED)
    except User.DoesNotExist:
        return Response({
            'error': 'Invalid credentials'
        }, status=status.HTTP_401_UNAUTHORIZED)
    

def is_admin_user(user):
    """Check if user has admin privileges"""
    return user.is_authenticated and (user.admin or user.staff or user.designation in ['manager', 'director', 'senior_manager'])

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_users(request):
    """List all users - Admin only"""
    if not is_admin_user(request.user):
        return Response({
            'error': 'Admin privileges required'
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        # Get all users
        users = User.objects.all().order_by('-id')
        
        # Search functionality
        search = request.GET.get('search', '')
        if search:
            users = users.filter(
                Q(email__icontains=search) | # type: ignore
                Q(first_name__icontains=search) | # type: ignore
                Q(last_name__icontains=search) | # type: ignore
                Q(designation__icontains=search) # type: ignore
            )
        
        # Filter by status
        status_filter = request.GET.get('status', '')
        if status_filter == 'active':
            users = users.filter(active=True)
        elif status_filter == 'inactive':
            users = users.filter(active=False)
        
        # Pagination
        page_size = min(int(request.GET.get('page_size', 50)), 100)
        paginator = paginator(users, page_size)
        page_number = request.GET.get('page', 1)
        page_obj = paginator.get_page(page_number)
        
        # Serialize users
        users_data = []
        for user in page_obj:
            users_data.append({
                'id': user.id,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'full_name': user.get_full_name(),
                'designation': user.designation,
                'company': user.company,
                'is_active': user.active,
                'is_staff': user.staff,
                'is_admin': user.admin,
                'last_login': user.last_login,
                'date_joined': user.id,  # Using ID as proxy for join date
                'role': user.get_role_display()
            })
        
        return Response({
            'users': users_data,
            'pagination': {
                'current_page': page_obj.number,
                'total_pages': paginator.num_pages,
                'total_count': paginator.count,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous()
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'error': f'Failed to fetch users: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def user_detail(request, user_id):
    """Get, update, or delete a specific user - Admin only"""
    if not is_admin_user(request.user):
        return Response({
            'error': 'Admin privileges required'
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({
            'error': 'User not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'GET':
        # Get user details
        return Response({
            'user': {
                'id': user.id,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'full_name': user.get_full_name(),
                'designation': user.designation,
                'company': user.company,
                'is_active': user.active,
                'is_staff': user.staff,
                'is_admin': user.admin,
                'last_login': user.last_login,
                'role': user.get_role_display()
            }
        }, status=status.HTTP_200_OK)
    
    elif request.method == 'PUT':
        # Update user
        try:
            # Prevent users from editing themselves to remove admin privileges
            if user.id == request.user.id:
                if 'is_admin' in request.data and not request.data.get('is_admin'):
                    return Response({
                        'error': 'Cannot remove your own admin privileges'
                    }, status=status.HTTP_400_BAD_REQUEST)
                if 'is_active' in request.data and not request.data.get('is_active'):
                    return Response({
                        'error': 'Cannot deactivate your own account'
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            # Update allowed fields
            allowed_fields = {
                'first_name': str,
                'last_name': str,
                'designation': str,
                'company': str,
                'is_active': bool,
                'is_staff': bool,
                'is_admin': bool
            }
            
            updated_fields = []
            for field, field_type in allowed_fields.items():
                if field in request.data:
                    value = request.data[field]
                    
                    # Handle boolean fields properly
                    if field_type == bool:
                        if isinstance(value, str):
                            value = value.lower() in ['true', '1', 'yes']
                        else:
                            value = bool(value)
                    
                    # Map frontend field names to model field names
                    model_field = field
                    if field == 'is_active':
                        model_field = 'active'
                    elif field == 'is_staff':
                        model_field = 'staff'
                    elif field == 'is_admin':
                        model_field = 'admin'
                    
                    setattr(user, model_field, value)
                    updated_fields.append(field)
            
            if updated_fields:
                user.save()
                
                return Response({
                    'message': 'User updated successfully',
                    'updated_fields': updated_fields,
                    'user': {
                        'id': user.id,
                        'email': user.email,
                        'first_name': user.first_name,
                        'last_name': user.last_name,
                        'full_name': user.get_full_name(),
                        'designation': user.designation,
                        'company': user.company,
                        'is_active': user.active,
                        'is_staff': user.staff,
                        'is_admin': user.admin,
                        'role': user.get_role_display()
                    }
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'message': 'No valid fields to update'
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            return Response({
                'error': f'Failed to update user: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        # Delete user
        try:
            # Prevent users from deleting themselves
            if user.id == request.user.id:
                return Response({
                    'error': 'Cannot delete your own account'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            user_email = user.email
            user.delete()
            
            return Response({
                'message': f'User {user_email} deleted successfully'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': f'Failed to delete user: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_user(request):
    """Create a new user - Admin only"""
    if not is_admin_user(request.user):
        return Response({
            'error': 'Admin privileges required'
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        email = request.data.get('email')
        password = request.data.get('password')
        first_name = request.data.get('first_name', '')
        last_name = request.data.get('last_name', '')
        designation = request.data.get('designation', 'employee')
        company = request.data.get('company', 'Mobiux')
        is_active = request.data.get('is_active', True)
        is_staff = request.data.get('is_staff', False)
        is_admin = request.data.get('is_admin', False)
        
        # Validation
        if not email or not password:
            return Response({
                'error': 'Email and password are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if user already exists
        if User.objects.filter(email=email).exists():
            return Response({
                'error': 'User with this email already exists'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate designation
        valid_designations = [choice[0] for choice in User.DESIGNATION_CHOICES]
        if designation not in valid_designations:
            return Response({
                'error': f'Invalid designation. Must be one of: {", ".join(valid_designations)}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create user
        user = User.objects.create_user(
            email=email,
            password=password
        )
        
        # Set additional fields
        user.first_name = first_name
        user.last_name = last_name
        user.designation = designation
        user.company = company
        
        # Handle boolean fields properly
        if isinstance(is_active, str):
            user.active = is_active.lower() in ['true', '1', 'yes']
        else:
            user.active = bool(is_active)
            
        if isinstance(is_staff, str):
            user.staff = is_staff.lower() in ['true', '1', 'yes']
        else:
            user.staff = bool(is_staff)
            
        if isinstance(is_admin, str):
            user.admin = is_admin.lower() in ['true', '1', 'yes']
        else:
            user.admin = bool(is_admin)
        
        user.save()
        
        return Response({
            'message': 'User created successfully',
            'user': {
                'id': user.id,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'full_name': user.get_full_name(),
                'designation': user.designation,
                'company': user.company,
                'is_active': user.active,
                'is_staff': user.staff,
                'is_admin': user.admin,
                'role': user.get_role_display()
            }
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response({
            'error': f'Failed to create user: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def toggle_user_status(request, user_id):
    """Block/Unblock a user - Admin only"""
    if not is_admin_user(request.user):
        return Response({
            'error': 'Admin privileges required'
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({
            'error': 'User not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Prevent users from blocking themselves
    if user.id == request.user.id:
        return Response({
            'error': 'Cannot block/unblock your own account'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Toggle active status
        user.active = not user.active
        user.save()
        
        action = 'unblocked' if user.active else 'blocked'
        
        return Response({
            'message': f'User {user.email} {action} successfully',
            'user': {
                'id': user.id,
                'email': user.email,
                'full_name': user.get_full_name(),
                'is_active': user.active
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'error': f'Failed to toggle user status: {str(e)}'
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_choices(request):
    """Get user field choices - Admin only"""
    if not is_admin_user(request.user):
        return Response({
            'error': 'Admin privileges required'
        }, status=status.HTTP_403_FORBIDDEN)
    
    return Response({
        'designations': dict(User.DESIGNATION_CHOICES),
        'status_choices': {
            'active': 'Active',
            'inactive': 'Inactive'
        }
    }, status=status.HTTP_200_OK)