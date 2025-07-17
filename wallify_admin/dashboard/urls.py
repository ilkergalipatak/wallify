from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.home, name='home'),
    path('collections/', views.collection_list, name='collection_list'),
    path('collections/create/', views.collection_create, name='collection_create'),
    path('collections/<int:pk>/', views.collection_detail, name='collection_detail'),
    path('collections/<int:pk>/edit/', views.collection_edit, name='collection_edit'),
    path('collections/<int:pk>/delete/', views.collection_delete, name='collection_delete'),
    
    path('files/', views.file_list, name='file_list'),
    path('files/upload/', views.file_upload, name='file_upload'),
    path('files/bulk-upload/', views.bulk_upload, name='bulk_upload'),
    path('files/<int:pk>/', views.file_detail, name='file_detail'),
    path('files/<int:pk>/edit/', views.file_edit, name='file_edit'),
    path('files/<int:pk>/delete/', views.file_delete, name='file_delete'),
    
    path('sync-with-cdn/', views.sync_with_cdn, name='sync_with_cdn'),
    
    # API endpoints
    path('api/collections/', views.api_collections, name='api_collections'),
    path('api/files/', views.api_files, name='api_files'),
    path('api/delete-file/', views.api_delete_file_endpoint, name='api_delete_file'),
    
    # Add proxy-image view
    path('proxy-image/', views.proxy_image, name='proxy_image'),
] 