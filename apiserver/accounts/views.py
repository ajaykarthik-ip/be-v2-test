from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import login, logout
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.contrib.auth import authenticate
import json
from .models import User

# YOUR EXISTING VIEWS
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
        user.save()
        
        print(f"DEBUG: User created successfully - ID: {user.id}")
        
        return Response({
            'message': 'User created successfully',
            'user': {
                'id': user.id,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name
            }
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        print(f"DEBUG: Exception: {str(e)}")
        import traceback
        traceback.print_exc()
        return Response({
            'error': f'Internal server error: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ADD THESE NEW AUTHENTICATION VIEWS BELOW:

# CORS Helper Function
def add_cors_headers(response, request):
    """Add CORS headers to response"""
    origin = request.headers.get('Origin')
    allowed_origins = [
        'http://localhost:3000',
        'http://127.0.0.1:3000',
        'http://localhost:8000',
        'http://127.0.0.1:8000'
    ]
    
    if origin and origin in allowed_origins:
        response["Access-Control-Allow-Origin"] = origin
    
    response["Access-Control-Allow-Credentials"] = "true"
    response["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS, PUT, DELETE"
    response["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-CSRFToken, X-Requested-With"
    response["Access-Control-Max-Age"] = "86400"
    return response


@csrf_exempt
@require_http_methods(["POST", "OPTIONS"])
def login_view(request):
    """Login user - Pure Django view"""
    if request.method == 'OPTIONS':
        response = JsonResponse({'status': 'ok'})
        return add_cors_headers(response, request)
        
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            email = data.get('email')
            password = data.get('password')
            
            if not email or not password:
                response = JsonResponse({
                    'error': 'Email and password are required'
                }, status=400)
                return add_cors_headers(response, request)
            
            # Find user by email
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                response = JsonResponse({
                    'error': 'Invalid email or password'
                }, status=400)
                return add_cors_headers(response, request)
            
            # Authenticate with username (since Django expects username)
            user = authenticate(username=user.email, password=password)
            
            if user and user.is_active:
                login(request, user)
                response = JsonResponse({
                    'message': 'Login successful',
                    'user': {
                        'id': user.id,
                        'email': user.email,
                        'first_name': user.first_name,
                        'last_name': user.last_name
                    }
                }, status=200)
                return add_cors_headers(response, request)
            else:
                response = JsonResponse({
                    'error': 'Invalid email or password'
                }, status=400)
                return add_cors_headers(response, request)
                
        except Exception as e:
            response = JsonResponse({'error': str(e)}, status=400)
            return add_cors_headers(response, request)
    
    response = JsonResponse({'error': 'Method not allowed'}, status=405)
    return add_cors_headers(response, request)


@csrf_exempt
@require_http_methods(["POST", "OPTIONS"])
def logout_view(request):
    """Logout user - Pure Django view"""
    if request.method == 'OPTIONS':
        response = JsonResponse({'status': 'ok'})
        return add_cors_headers(response, request)
        
    if request.method == 'POST':
        try:
            if request.user.is_authenticated:
                logout(request)
                response = JsonResponse({'message': 'Logout successful'}, status=200)
                return add_cors_headers(response, request)
            response = JsonResponse({'error': 'Not authenticated'}, status=401)
            return add_cors_headers(response, request)
        except Exception as e:
            response = JsonResponse({'error': str(e)}, status=400)
            return add_cors_headers(response, request)
    
    response = JsonResponse({'error': 'Method not allowed'}, status=405)
    return add_cors_headers(response, request)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_profile(request):
    """Get current user profile"""
    return Response({
        'user': {
            'id': request.user.id,
            'email': request.user.email,
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
            'is_staff': request.user.is_staff,
            'is_active': request.user.is_active
        }
    }, status=status.HTTP_200_OK)


@csrf_exempt
@require_http_methods(["GET", "OPTIONS"])
def csrf_token(request):
    """Get CSRF token for frontend"""
    if request.method == 'OPTIONS':
        response = JsonResponse({'status': 'ok'})
        return add_cors_headers(response, request)
        
    from django.middleware.csrf import get_token
    response = JsonResponse({
        'csrfToken': get_token(request)
    })
    return add_cors_headers(response, request)


@csrf_exempt
@require_http_methods(["GET", "POST", "OPTIONS"])
def cors_test(request):
    """Test CORS configuration - DEBUG VIEW"""
    
    print(f"🧪 CORS Test: {request.method} request from {request.headers.get('Origin', 'unknown origin')}")
    
    if request.method == "OPTIONS":
        print("✈️ Handling preflight OPTIONS request")
        response = JsonResponse({'status': 'preflight ok'})
    else:
        print("📡 Handling actual request")
        response = JsonResponse({
            'status': 'CORS test successful! 🎉',
            'method': request.method,
            'origin': request.headers.get('Origin', 'No origin header'),
            'user_agent': request.headers.get('User-Agent', 'No user agent'),
            'cookies_received': len(request.COOKIES),
        })
    
    return add_cors_headers(response, request)


# GOOGLE OAUTH (Optional - requires google-auth package)
@csrf_exempt
@require_http_methods(["POST", "OPTIONS"])
def google_login_view(request):
    """Login/Register user with Google OAuth - Simplified version"""
    if request.method == 'OPTIONS':
        response = JsonResponse({'status': 'ok'})
        return add_cors_headers(response, request)
        
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            # For now, return a placeholder response
            # TODO: Implement actual Google OAuth verification
            response = JsonResponse({
                'error': 'Google OAuth not implemented yet',
                'message': 'Please use regular email/password login'
            }, status=501)
            return add_cors_headers(response, request)
            
        except Exception as e:
            response = JsonResponse({
                'error': 'Google login failed',
                'details': str(e)
            }, status=400)
            return add_cors_headers(response, request)
    
    response = JsonResponse({'error': 'Method not allowed'}, status=405)
    return add_cors_headers(response, request)