from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json
from .models import Project
from .serializers import ProjectSerializer, ProjectListSerializer
from django.core.paginator import Paginator
from django.db.models import Prefetch

@api_view(['GET', 'POST'])  # ✅ CHANGED: Use DRF decorators
@permission_classes([IsAuthenticated])  # ✅ CHANGED: Use DRF permissions
def project_list_create(request):
    """
    GET: List all projects
    POST: Create new project
    """
    if request.method == 'GET':
        projects = Project.objects.all()
        
        # Filter by status if provided
        status_filter = request.GET.get('status')
        if status_filter:
            projects = projects.filter(status=status_filter)
        
        # Filter by billable if provided
        billable = request.GET.get('billable')
        if billable is not None:
            projects = projects.filter(billable=billable.lower() == 'true')
        
        # Search by name
        search = request.GET.get('search')
        if search:
            projects = projects.filter(name__icontains=search)
        
        serializer = ProjectListSerializer(projects, many=True)
        return Response({
            'count': projects.count(),
            'projects': serializer.data
        })
    
    elif request.method == 'POST':
        serializer = ProjectSerializer(data=request.data)
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    project = serializer.save()
                return Response({
                    'message': 'Project created successfully',
                    'project': ProjectSerializer(project).data
                }, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response({
                    'error': 'Failed to create project',
                    'details': str(e)
                }, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'PUT', 'DELETE'])  # ✅ CHANGED: Use DRF decorators
@permission_classes([IsAuthenticated])  # ✅ CHANGED: Use DRF permissions
def project_detail(request, pk):
    """
    GET: Retrieve project by ID
    PUT: Update project
    DELETE: Delete project
    """
    try:
        project = Project.objects.get(pk=pk)
    except Project.DoesNotExist:
        return Response({'error': 'Project not found'}, status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'GET':
        serializer = ProjectSerializer(project)
        return Response({
            'project': serializer.data
        })
    
    elif request.method == 'PUT':
        serializer = ProjectSerializer(project, data=request.data, partial=True)
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    project = serializer.save()
                return Response({
                    'message': 'Project updated successfully',
                    'project': ProjectSerializer(project).data
                })
            except Exception as e:
                return Response({
                    'error': 'Failed to update project',
                    'details': str(e)
                }, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        try:
            with transaction.atomic():
                project.delete()
            return Response({
                'message': 'Project deleted successfully'
            }, status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({
                'error': 'Failed to delete project',
                'details': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def project_choices(request):
    """Get choices for dropdowns"""
    return Response({
        'statuses': dict(Project.STATUS_CHOICES)
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def active_projects_list(request):
    """Get list of active projects for dropdowns"""
    projects = Project.objects.filter(status='active').values('id', 'name', 'billable')
    
    return Response({
        'projects': list(projects)
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def debug_project_create(request):
    """Debug endpoint to see what's happening"""
    serializer = ProjectSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({
            'validation_errors': serializer.errors,
            'received_data': request.data
        }, status=status.HTTP_400_BAD_REQUEST)
    
    return Response({'message': 'Validation passed'})