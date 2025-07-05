from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('api/devices/', views.get_devices, name='get_devices'),
    path('api/update-status/', views.update_status, name='update_status'),
    path('reports/', views.metrics_report_view, name='metrics_report'),
    path('api/devices/add/', views.add_device, name='add_device'),
    path('view_log/',         views.view_log,       name='view_log'),
    path('api/logs/',         views.api_logs,       name='api_logs'),
    path('api/logs/clear/',   views.api_clear_logs, name='api_clear_logs'),
    path('api/devices/<int:device_id>/', views.device_detail, name='device_detail'),
    path('api/metrics/<int:device_id>/', views.get_metrics, name='get_metrics'),
    path('api/export-metrics/<int:device_id>/', views.export_metrics_csv, name='export_metrics_csv'),
    path('reports/',             views.reports_view,      name='reports'),
    path('api/reports/metrics/', views.api_report_metrics, name='api_report_metrics'),
    path('api/reports/alerts/',  views.api_report_alerts,  name='api_report_alerts'),
    path('api/logs/<int:log_id>/ack/', views.api_toggle_ack, name='toggle_ack'),
]
