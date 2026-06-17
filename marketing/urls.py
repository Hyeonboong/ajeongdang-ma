from django.urls import path

from . import views

app_name = "marketing"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("campaigns/", views.campaign_list, name="campaign_list"),
    path("campaigns/create/", views.campaign_create, name="campaign_create"),
    path("campaigns/<int:pk>/", views.campaign_detail, name="campaign_detail"),
    path("campaigns/<int:pk>/update/", views.campaign_update, name="campaign_update"),
    path("campaigns/<int:pk>/delete/", views.campaign_delete, name="campaign_delete"),
    path("campaigns/<int:pk>/tracking-links/create/", views.tracking_link_create, name="tracking_link_create"),
    path("tracking-links/<int:pk>/events/create/", views.tracking_event_create, name="tracking_event_create"),
    path("r/<slug:code>/", views.tracking_redirect, name="tracking_redirect"),
    path("performances/upload/", views.performance_upload, name="performance_upload"),
    path("youtube/channels/", views.youtube_channel_list, name="youtube_channel_list"),
    path("youtube/channels/create/", views.youtube_channel_create, name="youtube_channel_create"),
    path("youtube/channels/<int:pk>/", views.youtube_channel_detail, name="youtube_channel_detail"),
    path("youtube/channels/<int:pk>/delete/", views.youtube_channel_delete, name="youtube_channel_delete"),
    path("youtube/analyze/", views.youtube_analyze, name="youtube_analyze"),
    path("youtube/results/<int:pk>/", views.youtube_result, name="youtube_result"),
    path("youtube/channel-analyze/", views.youtube_channel_analyze, name="youtube_channel_analyze"),
    path("youtube/channel-results/<int:pk>/", views.youtube_channel_result, name="youtube_channel_result"),
]
