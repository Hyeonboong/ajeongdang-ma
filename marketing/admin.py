from django.contrib import admin

from .models import (
    Campaign,
    CampaignPerformance,
    ConversionEvent,
    TrackingLink,
    YouTubeChannel,
    YouTubeChannelAnalysis,
    YouTubeInfluencerAnalysis,
    YouTubeRecentVideo,
)


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "objective",
        "service_type",
        "status",
        "channel",
        "ad_type",
        "youtube_channel",
        "cost",
        "start_date",
        "end_date",
        "created_at",
    )
    list_filter = ("objective", "service_type", "status", "channel", "ad_type", "youtube_channel", "start_date")
    search_fields = ("name", "channel", "ad_type", "memo", "youtube_channel__channel_name")


@admin.register(CampaignPerformance)
class CampaignPerformanceAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "campaign",
        "date",
        "impressions",
        "clicks",
        "consultations",
        "contracts",
        "ctr",
        "consultation_rate",
        "contract_rate",
        "cost_per_consultation",
        "cost_per_contract",
        "created_at",
    )
    list_filter = ("date", "campaign__channel", "campaign__ad_type")
    search_fields = ("campaign__name", "ad_copy")
    readonly_fields = (
        "ctr",
        "consultation_rate",
        "contract_rate",
        "cost_per_consultation",
        "cost_per_contract",
    )


@admin.register(TrackingLink)
class TrackingLinkAdmin(admin.ModelAdmin):
    list_display = ("id", "campaign", "name", "code", "destination_url", "click_count", "consultation_count", "contract_count", "created_at")
    search_fields = ("campaign__name", "name", "code", "destination_url")
    list_filter = ("campaign__status", "campaign__ad_type")
    readonly_fields = ("code",)


@admin.register(ConversionEvent)
class ConversionEventAdmin(admin.ModelAdmin):
    list_display = ("id", "tracking_link", "event_type", "occurred_at")
    search_fields = ("tracking_link__name", "tracking_link__code", "tracking_link__campaign__name")
    list_filter = ("event_type", "occurred_at")


@admin.register(YouTubeInfluencerAnalysis)
class YouTubeInfluencerAnalysisAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "channel_name",
        "video_title",
        "campaign",
        "paid_amount",
        "view_count",
        "consultation_count",
        "contract_count",
        "cost_per_view",
        "cost_per_consultation",
        "cost_per_contract",
        "created_at",
    )
    list_filter = ("published_at", "campaign__channel")
    search_fields = ("channel_name", "video_title", "youtube_url", "campaign__name")
    readonly_fields = ("cost_per_view", "cost_per_consultation", "cost_per_contract")


@admin.register(YouTubeChannel)
class YouTubeChannelAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "channel_name",
        "main_content",
        "subscriber_count",
        "recent_avg_views",
        "recent_median_views",
        "subscriber_view_rate",
        "updated_at",
    )
    search_fields = ("channel_name", "main_content", "channel_url", "channel_id")
    list_filter = ("main_content",)
    readonly_fields = (
        "subscriber_count",
        "total_view_count",
        "video_count",
        "recent_video_count",
        "recent_avg_views",
        "recent_median_views",
        "recent_min_views",
        "recent_max_views",
        "recent_avg_likes",
        "recent_avg_comments",
        "subscriber_view_rate",
    )


class YouTubeRecentVideoInline(admin.TabularInline):
    model = YouTubeRecentVideo
    extra = 0


@admin.register(YouTubeChannelAnalysis)
class YouTubeChannelAnalysisAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "campaign",
        "channel_name",
        "subscriber_count",
        "recent_avg_views",
        "recent_median_views",
        "expected_paid_amount",
        "avg_cost_per_view",
        "median_cost_per_view",
        "created_at",
    )
    search_fields = ("campaign__name", "channel_name", "channel_url", "channel_id")
    readonly_fields = ("subscriber_view_rate", "avg_cost_per_view", "median_cost_per_view")
    inlines = [YouTubeRecentVideoInline]


@admin.register(YouTubeRecentVideo)
class YouTubeRecentVideoAdmin(admin.ModelAdmin):
    list_display = ("id", "analysis", "title", "view_count", "like_count", "comment_count", "published_at")
    search_fields = ("title", "video_id", "analysis__channel_name")
