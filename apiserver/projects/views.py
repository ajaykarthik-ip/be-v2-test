import logging
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db import transaction
from .models import Project
from .serializers import ProjectSerializer, ProjectListSerializer
from rest_framework import generics
from rest_framework.views import APIView

logger = logging.getLogger(__name__)

class ProjectListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return ProjectListSerializer
        return ProjectSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'count': queryset.count(),
            'projects': serializer.data  
        })

class ProjectDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated]

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', True)  # partial update
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

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

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        project_name = instance.name
        try:
            with transaction.atomic():
                instance.delete()

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

class ProjectChoicesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Return available project status choices."""
        return Response({'statuses': dict(Project.STATUS_CHOICES)})

class ActiveProjectsListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Project.objects.filter(status='active').values('id', 'name', 'billable')

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        return Response({'projects': list(queryset)})