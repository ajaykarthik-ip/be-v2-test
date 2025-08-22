import logging
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db import transaction
from django.shortcuts import get_object_or_404
from .models import Project
from .serializers import ProjectSerializer, ProjectListSerializer

logger = logging.getLogger(__name__)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def project_list_create(request):
    """List all projects or create a new project."""
    
    if request.method == 'GET':
        projects = Project.objects.all()
        
        status_filter = request.GET.get('status')
        if status_filter:
            projects = projects.filter(status=status_filter)
        
        billable = request.GET.get('billable')
        if billable is not None:
            projects = projects.filter(billable=billable.lower() == 'true')
        
        search = request.GET.get('search')
        if search:
            projects = projects.filter(name__icontains=search)
        
        serializer = ProjectListSerializer(projects, many=True)
        return Response({
            'count': projects.count(),
            'projects': serializer.data
        })
    
    serializer = ProjectSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        with transaction.atomic():
            project = serializer.save()
        
        logger.info(f"Project created successfully: {project.name}")
        return Response({
            'message': 'Project created successfully',
            'project': ProjectSerializer(project).data
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        logger.error(f"Project creation failed: {str(e)}", exc_info=True)
        return Response(
            {'error': 'Failed to create project'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def project_detail(request, pk):
    """Retrieve, update or delete a project."""
    project = get_object_or_404(Project, pk=pk)
    
    if request.method == 'GET':
        serializer = ProjectSerializer(project)
        return Response({'project': serializer.data})
    
    if request.method == 'PUT':
        serializer = ProjectSerializer(project, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            with transaction.atomic():
                project = serializer.save()
            
            logger.info(f"Project updated successfully: {project.name}")
            return Response({
                'message': 'Project updated successfully',
                'project': ProjectSerializer(project).data
            })
            
        except Exception as e:
            logger.error(f"Project update failed: {str(e)}", exc_info=True)
            return Response(
                {'error': 'Failed to update project'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    try:
        with transaction.atomic():
            project_name = project.name
            project.delete()
        
        logger.info(f"Project deleted successfully: {project_name}")
        return Response(
            {'message': 'Project deleted successfully'},
            status=status.HTTP_204_NO_CONTENT
        )
        
    except Exception as e:
        logger.error(f"Project deletion failed: {str(e)}", exc_info=True)
        return Response(
            {'error': 'Failed to delete project'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def project_choices(request):
    """Get available project status choices."""
    return Response({'statuses': dict(Project.STATUS_CHOICES)})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def active_projects_list(request):
    """Get list of active projects for dropdowns."""
    projects = Project.objects.filter(status='active').values('id', 'name', 'billable')
    return Response({'projects': list(projects)})