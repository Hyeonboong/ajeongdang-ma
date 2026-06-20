from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import (
    CampaignForm,
    MarketingSettingForm,
    TrackingLinkForm,
    YouTubeChannelAnalysisForm,
    YouTubeChannelForm,
    YoutubeAnalyzeForm,
)
from .models import (
    Campaign,
    ConversionEvent,
    MarketingSetting,
    TrackingLink,
    YouTubeChannel,
    YouTubeChannelAnalysis,
    YouTubeChannelRecentVideo,
    YouTubeInfluencerAnalysis,
    YouTubeRecentVideo,
    safe_divide,
)
from .services.youtube_service import (
    get_channel_analysis_metrics,
)


def dashboard(request):
    marketing_setting = MarketingSetting.load()
    campaigns = list(Campaign.objects.select_related("youtube_channel").prefetch_related("tracking_links__events"))
    campaign_summaries = []
    inefficient_contract_cost = marketing_setting.good_contract_cost
    for campaign in campaigns:
        video_views = campaign.youtube_channel.recent_avg_views if campaign.youtube_channel else 0
        tracking_links = list(campaign.tracking_links.all())
        clicks = sum(link.click_count for link in tracking_links)
        consultations = sum(link.consultation_count for link in tracking_links)
        contracts = sum(link.contract_count for link in tracking_links)
        cost_per_contract = safe_divide(campaign.cost, contracts)
        click_rate = safe_divide(clicks, video_views, 100)

        diagnosis = "양호"
        improvement = "성과 유지"
        if not campaign.youtube_channel:
            diagnosis = "채널 미연결"
            improvement = "협찬 유튜버 연결"
        elif not tracking_links:
            diagnosis = "링크 미등록"
            improvement = "전환 데이터 확인 필요"
        elif not clicks:
            diagnosis = "데이터 부족"
            improvement = "링크 노출 위치 점검"
        elif not consultations:
            diagnosis = "상담 전환 없음"
            improvement = "랜딩/상담 CTA 점검"
        elif not contracts:
            diagnosis = "가입 전환 없음"
            improvement = "상담 후 가입 흐름 점검"
        elif cost_per_contract >= inefficient_contract_cost:
            diagnosis = "비효율"
            improvement = "협찬비 재검토 필요"
        elif click_rate and click_rate < 0.1:
            diagnosis = "클릭률 낮음"
            improvement = "고정댓글/랜딩 문구 개선"

        campaign_summaries.append(
            {
                "campaign": campaign,
                "youtube_channel": campaign.youtube_channel,
                "video_views": video_views,
                "has_video_views": bool(video_views),
                "clicks": clicks,
                "consultations": consultations,
                "contracts": contracts,
                "click_rate": click_rate,
                "consultation_rate": safe_divide(consultations, clicks, 100),
                "contract_rate": safe_divide(contracts, consultations, 100),
                "expected_cost_per_view": safe_divide(campaign.cost, video_views) if video_views else None,
                "cost_per_consultation": safe_divide(campaign.cost, consultations),
                "cost_per_contract": cost_per_contract,
                "diagnosis": diagnosis,
                "improvement": improvement,
            }
        )

    active_statuses = ["컨택예정", "컨택중", "진행중"]
    campaign_summaries = sorted(
        campaign_summaries,
        key=lambda summary: (
            summary["campaign"].status not in active_statuses,
            -summary["campaign"].created_at.timestamp(),
        ),
    )

    channels = list(YouTubeChannel.objects.prefetch_related("recent_videos"))

    youtube_candidates = sorted(
        channels,
        key=lambda channel: (-channel.subscriber_view_rate, -channel.recent_median_views, channel.channel_name),
    )[:5]
    recent_analyses = YouTubeChannelAnalysis.objects.select_related("campaign").order_by("-created_at", "-id")[:5]
    exposure_campaigns = [summary for summary in campaign_summaries if summary["has_video_views"]]
    efficient_campaigns = sorted(exposure_campaigns, key=lambda summary: summary["expected_cost_per_view"])[:5]
    inefficient_campaigns = sorted(
        exposure_campaigns,
        key=lambda summary: summary["expected_cost_per_view"],
        reverse=True,
    )[:5]
    for summary in exposure_campaigns:
        summary["efficiency_comment"] = _cost_per_view_comment(summary["expected_cost_per_view"], marketing_setting)

    context = {
        "operation_metrics": {
            "channel_count": YouTubeChannel.objects.count(),
            "active_campaign_count": sum(1 for campaign in campaigns if campaign.status in active_statuses),
            "analysis_count": YouTubeChannelAnalysis.objects.count(),
            "tracking_link_count": TrackingLink.objects.count(),
        },
        "diagnostic_metrics": {
            "inefficient_campaign_count": len(inefficient_campaigns),
            "efficient_campaign_count": len(efficient_campaigns),
        },
        "efficient_campaigns": efficient_campaigns,
        "inefficient_campaigns": inefficient_campaigns,
        "campaign_summaries": campaign_summaries,
        "youtube_candidates": youtube_candidates,
        "recent_analyses": recent_analyses,
    }
    return render(request, "marketing/dashboard.html", context)


def _cost_per_view_comment(cost_per_view, setting=None):
    setting = setting or MarketingSetting.load()
    if cost_per_view <= setting.cpv_good_max:
        return "효율 좋음"
    if cost_per_view <= setting.cpv_normal_max:
        return "보통"
    if cost_per_view <= setting.cpv_review_max:
        return "단가 검토 필요"
    return "비용 부담 높음"


def marketing_settings(request):
    setting = MarketingSetting.load()
    if request.method == "POST":
        form = MarketingSettingForm(request.POST, instance=setting)
        if form.is_valid():
            form.save()
            messages.success(request, "효율 판단 기준이 저장되었습니다.")
            return redirect("marketing:marketing_settings")
    else:
        form = MarketingSettingForm(instance=setting)

    return render(
        request,
        "marketing/marketing_settings.html",
        {"form": form, "setting": setting},
    )


def campaign_list(request):
    campaigns = Campaign.objects.order_by("-created_at", "-id")
    return render(request, "marketing/campaign_list.html", {"campaigns": campaigns})


def campaign_create(request):
    if request.method == "POST":
        form = CampaignForm(request.POST)
        if form.is_valid():
            campaign = form.save()
            messages.success(request, "캠페인이 등록되었습니다.")
            return redirect("marketing:campaign_detail", pk=campaign.pk)
    else:
        form = CampaignForm()
    return render(request, "marketing/campaign_form.html", {"form": form, "is_update": False})


def campaign_update(request, pk):
    campaign = get_object_or_404(Campaign, pk=pk)
    if request.method == "POST":
        form = CampaignForm(request.POST, instance=campaign)
        if form.is_valid():
            campaign = form.save()
            messages.success(request, "캠페인이 수정되었습니다.")
            return redirect("marketing:campaign_detail", pk=campaign.pk)
    else:
        form = CampaignForm(instance=campaign)
    return render(request, "marketing/campaign_form.html", {"form": form, "campaign": campaign, "is_update": True})


def campaign_detail(request, pk):
    campaign = get_object_or_404(
        Campaign.objects.select_related("youtube_channel").prefetch_related("tracking_links__events"),
        pk=pk,
    )
    tracking_links = campaign.tracking_links.all()
    tracking_summary = {
        "video_views": 0,
        "clicks": sum(link.click_count for link in tracking_links),
        "consultations": sum(link.consultation_count for link in tracking_links),
        "contracts": sum(link.contract_count for link in tracking_links),
    }
    if campaign.youtube_channel:
        tracking_summary["video_views"] = campaign.youtube_channel.recent_avg_views or 0
    tracking_summary["cost_per_view"] = safe_divide(campaign.cost, tracking_summary["video_views"])
    tracking_summary["click_rate"] = safe_divide(
        tracking_summary["clicks"],
        tracking_summary["video_views"],
        100,
    )
    tracking_summary["consultation_rate"] = safe_divide(
        tracking_summary["consultations"],
        tracking_summary["clicks"],
        100,
    )
    tracking_summary["contract_rate"] = safe_divide(
        tracking_summary["contracts"],
        tracking_summary["consultations"],
        100,
    )
    tracking_summary["click_to_contract_rate"] = safe_divide(
        tracking_summary["contracts"],
        tracking_summary["clicks"],
        100,
    )
    tracking_summary["cost_per_click"] = safe_divide(campaign.cost, tracking_summary["clicks"])
    tracking_summary["cost_per_consultation"] = safe_divide(campaign.cost, tracking_summary["consultations"])
    tracking_summary["cost_per_contract"] = safe_divide(campaign.cost, tracking_summary["contracts"])
    return render(
        request,
        "marketing/campaign_detail.html",
        {
            "campaign": campaign,
            "tracking_links": tracking_links,
            "tracking_link_form": TrackingLinkForm(),
            "tracking_summary": tracking_summary,
        },
    )


@require_POST
def campaign_delete(request, pk):
    campaign = get_object_or_404(Campaign, pk=pk)
    campaign.delete()
    messages.success(request, "캠페인이 삭제되었습니다.")
    return redirect("marketing:campaign_list")


@require_POST
def tracking_link_create(request, pk):
    campaign = get_object_or_404(Campaign, pk=pk)
    form = TrackingLinkForm(request.POST)
    if form.is_valid():
        tracking_link = form.save(commit=False)
        tracking_link.campaign = campaign
        tracking_link.save()
        messages.success(request, "성과 추적 링크가 등록되었습니다.")
    else:
        messages.error(request, "추적 링크 정보를 다시 확인해주세요.")
    return redirect("marketing:campaign_detail", pk=campaign.pk)


@require_POST
def tracking_event_create(request, pk):
    tracking_link = get_object_or_404(TrackingLink.objects.select_related("campaign"), pk=pk)
    event_type = request.POST.get("event_type")
    valid_event_types = {choice[0] for choice in ConversionEvent.EventType.choices}
    if event_type not in valid_event_types:
        messages.error(request, "등록할 수 없는 전환 이벤트입니다.")
        return redirect("marketing:campaign_detail", pk=tracking_link.campaign.pk)

    ConversionEvent.objects.create(tracking_link=tracking_link, event_type=event_type)
    messages.success(request, "전환 이벤트가 추가되었습니다.")
    return redirect("marketing:campaign_detail", pk=tracking_link.campaign.pk)


def tracking_redirect(request, code):
    tracking_link = get_object_or_404(TrackingLink, code=code)
    ConversionEvent.objects.create(tracking_link=tracking_link, event_type=ConversionEvent.EventType.CLICK)
    return redirect(tracking_link.destination_url)


def youtube_channel_list(request):
    query = request.GET.get("q", "").strip()
    channels = YouTubeChannel.objects.all()
    if query:
        channels = channels.filter(channel_name__icontains=query)
    return render(request, "marketing/youtube_channel_list.html", {"channels": channels, "query": query})


def youtube_channel_create(request):
    if request.method == "POST":
        form = YouTubeChannelForm(request.POST)
        if form.is_valid():
            channel = form.save(commit=False)
            manual_channel_name = channel.channel_name.strip()
            try:
                metrics = get_channel_analysis_metrics(channel.channel_url, limit=10)
            except Exception as exc:
                messages.error(request, f"채널 정보를 불러오지 못했습니다: {exc}")
                return render(request, "marketing/youtube_channel_form.html", {"form": form})

            _apply_youtube_channel_metrics(channel, metrics, manual_channel_name=manual_channel_name)
            channel.save()
            _replace_youtube_channel_recent_videos(channel, metrics.get("recent_videos", []))
            messages.success(request, "유튜버 채널이 저장되었습니다.")
            return redirect("marketing:youtube_channel_detail", pk=channel.pk)
    else:
        form = YouTubeChannelForm()
    return render(request, "marketing/youtube_channel_form.html", {"form": form})


def youtube_channel_detail(request, pk):
    channel = get_object_or_404(YouTubeChannel.objects.prefetch_related("recent_videos"), pk=pk)
    campaigns = channel.campaigns.order_by("-created_at", "-id")
    return render(
        request,
        "marketing/youtube_channel_detail.html",
        {"channel": channel, "campaigns": campaigns, "recent_videos": channel.recent_videos.all()},
    )


@require_POST
def youtube_channel_sync(request, pk):
    channel = get_object_or_404(YouTubeChannel, pk=pk)
    try:
        metrics = get_channel_analysis_metrics(channel.channel_url, limit=10)
    except Exception as exc:
        messages.error(request, f"채널 동기화 중 오류가 발생했습니다: {exc}")
        return redirect("marketing:youtube_channel_list")

    _apply_youtube_channel_metrics(channel, metrics, manual_channel_name=channel.channel_name)
    channel.save()
    _replace_youtube_channel_recent_videos(channel, metrics.get("recent_videos", []))
    messages.success(request, "유튜버 채널 지표가 동기화되었습니다.")
    return redirect("marketing:youtube_channel_detail", pk=channel.pk)


@require_POST
def youtube_channel_delete(request, pk):
    channel = get_object_or_404(YouTubeChannel, pk=pk)
    channel.delete()
    messages.success(request, "유튜버 채널이 삭제되었습니다.")
    return redirect("marketing:youtube_channel_list")


def youtube_analyze(request):
    recent_results = YouTubeInfluencerAnalysis.objects.all()[:5]
    campaign_defaults = _youtube_analysis_campaign_defaults()
    if request.method == "POST":
        form = YoutubeAnalyzeForm(request.POST)
        if form.is_valid():
            campaign = form.cleaned_data["campaign"]
            default_values = campaign_defaults.get(str(campaign.pk), {})
            paid_amount = campaign.cost
            consultation_count = form.cleaned_data.get("consultation_count")
            contract_count = form.cleaned_data.get("contract_count")
            if consultation_count in [None, ""]:
                consultation_count = default_values.get("consultation_count") or 0
            if contract_count in [None, ""]:
                contract_count = default_values.get("contract_count") or 0

            youtube_channel = campaign.youtube_channel

            analysis = YouTubeInfluencerAnalysis.objects.create(
                campaign=campaign,
                youtube_url="",
                channel_name=youtube_channel.channel_name if youtube_channel else campaign.channel,
                subscriber_count=youtube_channel.subscriber_count if youtube_channel else 0,
                video_title=f"{campaign.name} 전환 성과 분석",
                view_count=0,
                like_count=0,
                comment_count=0,
                published_at=None,
                paid_amount=paid_amount,
                consultation_count=consultation_count or 0,
                contract_count=contract_count or 0,
            )
            messages.success(request, "캠페인 전환 성과 분석이 저장되었습니다.")
            return redirect("marketing:youtube_result", pk=analysis.pk)
    else:
        form = YoutubeAnalyzeForm()
    return render(
        request,
        "marketing/youtube_analyze.html",
        {"form": form, "recent_results": recent_results, "campaign_defaults": campaign_defaults},
    )


def _youtube_analysis_campaign_defaults():
    defaults = {}
    campaigns = Campaign.objects.prefetch_related("tracking_links__events", "youtube_analyses").order_by("-created_at", "-id")
    for campaign in campaigns:
        tracking_links = list(campaign.tracking_links.all())
        defaults[str(campaign.pk)] = {
            "paid_amount": campaign.cost,
            "consultation_count": sum(link.consultation_count for link in tracking_links),
            "contract_count": sum(link.contract_count for link in tracking_links),
        }
    return defaults


def youtube_result(request, pk):
    analysis = get_object_or_404(YouTubeInfluencerAnalysis, pk=pk)
    marketing_setting = MarketingSetting.load()

    if not analysis.consultation_count and not analysis.contract_count:
        efficiency_message = "아직 상담/가입 데이터가 부족합니다. 추적 링크 이벤트가 쌓이면 전환 효율을 판단할 수 있습니다."
    elif analysis.cost_per_contract and analysis.cost_per_contract <= marketing_setting.good_contract_cost:
        efficiency_message = "지급 광고비 대비 가입 전환 효율이 좋은 캠페인입니다."
    else:
        efficiency_message = "상담 수와 가입 수를 기준으로 협찬비 또는 캠페인 메시지 재검토가 필요합니다."

    return render(
        request,
        "marketing/youtube_result.html",
        {
            "analysis": analysis,
            "efficiency_message": efficiency_message,
        },
    )


def youtube_channel_analyze(request):
    recent_analyses = YouTubeChannelAnalysis.objects.select_related("campaign")[:10]
    if request.method == "POST":
        form = YouTubeChannelAnalysisForm(request.POST)
        if form.is_valid():
            campaign = form.cleaned_data["campaign"]
            youtube_channel = campaign.youtube_channel
            channel_url = youtube_channel.channel_url
            expected_paid_amount = form.cleaned_data["expected_paid_amount"]
            try:
                metrics = get_channel_analysis_metrics(channel_url, limit=10)
            except Exception as exc:
                messages.error(request, f"유튜버 단가 분석 중 오류가 발생했습니다: {exc}")
                return render(
                    request,
                    "marketing/youtube_channel_analyze.html",
                    {"form": form, "recent_analyses": recent_analyses},
                )

            _apply_youtube_channel_metrics(youtube_channel, metrics, manual_channel_name=youtube_channel.channel_name)
            youtube_channel.save()
            _replace_youtube_channel_recent_videos(youtube_channel, metrics.get("recent_videos", []))

            analysis = YouTubeChannelAnalysis.objects.create(
                campaign=campaign,
                channel_url=channel_url,
                channel_id=youtube_channel.channel_id or metrics["channel_id"],
                channel_name=youtube_channel.channel_name or metrics["channel_name"],
                subscriber_count=youtube_channel.subscriber_count or metrics["subscriber_count"],
                total_view_count=youtube_channel.total_view_count or metrics["total_view_count"],
                video_count=youtube_channel.video_count or metrics["video_count"],
                recent_video_count=youtube_channel.recent_video_count or metrics["recent_video_count"],
                recent_avg_views=youtube_channel.recent_avg_views or metrics["recent_avg_views"],
                recent_median_views=youtube_channel.recent_median_views or metrics["recent_median_views"],
                recent_min_views=youtube_channel.recent_min_views or metrics["recent_min_views"],
                recent_max_views=youtube_channel.recent_max_views or metrics["recent_max_views"],
                expected_paid_amount=expected_paid_amount,
            )
            for video in metrics["recent_videos"]:
                YouTubeRecentVideo.objects.create(
                    analysis=analysis,
                    video_id=video["video_id"],
                    title=video["title"],
                    view_count=video["view_count"],
                    like_count=video["like_count"],
                    comment_count=video["comment_count"],
                    published_at=video["published_at"],
                )
            messages.success(request, "유튜버 채널 단가 사전 분석이 저장되었습니다.")
            return redirect("marketing:youtube_channel_result", pk=analysis.pk)
    else:
        form = YouTubeChannelAnalysisForm()
    return render(request, "marketing/youtube_channel_analyze.html", {"form": form, "recent_analyses": recent_analyses})


def youtube_channel_result(request, pk):
    analysis = get_object_or_404(YouTubeChannelAnalysis.objects.prefetch_related("recent_videos"), pk=pk)
    judgment_messages = _build_channel_judgment_messages(analysis)
    return render(
        request,
        "marketing/youtube_channel_result.html",
        {"analysis": analysis, "judgment_messages": judgment_messages},
    )


def _build_channel_judgment_messages(analysis):
    messages_list = []
    if analysis.recent_median_views and analysis.recent_avg_views >= analysis.recent_median_views * 1.4:
        messages_list.append("평균 조회수가 중앙값보다 높아 일부 인기 영상이 평균을 끌어올린 채널입니다.")
    if analysis.subscriber_view_rate >= 50:
        messages_list.append("구독자 대비 평균 조회율이 높아 채널 충성도가 좋은 편입니다.")
    if analysis.median_cost_per_view >= 100:
        messages_list.append("중앙값 기준 조회당 비용이 높아 협찬비 조정이 필요합니다.")
    elif analysis.median_cost_per_view > 0:
        messages_list.append("중앙값 기준 조회당 비용이 낮아 노출 효율이 좋은 편입니다.")
    if not messages_list:
        messages_list.append("최근 조회수와 예상 협찬비를 함께 보며 추가 검토가 필요합니다.")
    return messages_list


def _text(value):
    if value is None:
        return ""
    return "" if str(value) == "nan" else str(value).strip()


def _int_value(value):
    if value is None or str(value) == "nan" or value == "":
        return 0
    return int(float(value))


def _date_value(value):
    if value is None or str(value) == "nan" or value == "":
        return None
    if hasattr(value, "date"):
        return value.date()
    return value


def _average(values):
    if not values:
        return 0
    return round(sum(values) / len(values), 2)


def _apply_youtube_channel_metrics(channel, metrics, manual_channel_name=""):
    recent_videos = metrics.get("recent_videos", [])
    channel.channel_id = metrics["channel_id"]
    channel.channel_name = manual_channel_name or metrics["channel_name"]
    channel.subscriber_count = metrics["subscriber_count"]
    channel.total_view_count = metrics["total_view_count"]
    channel.video_count = metrics["video_count"]
    channel.recent_video_count = metrics["recent_video_count"]
    channel.recent_latest_views = metrics.get("recent_latest_views", 0)
    channel.recent_avg_views = metrics["recent_avg_views"]
    channel.recent_median_views = metrics["recent_median_views"]
    channel.recent_min_views = metrics["recent_min_views"]
    channel.recent_max_views = metrics["recent_max_views"]
    channel.recent_avg_likes = _average([video["like_count"] for video in recent_videos])
    channel.recent_avg_comments = _average([video["comment_count"] for video in recent_videos])


def _replace_youtube_channel_recent_videos(channel, recent_videos):
    channel.recent_videos.all().delete()
    YouTubeChannelRecentVideo.objects.bulk_create(
        [
            YouTubeChannelRecentVideo(
                channel=channel,
                video_id=video["video_id"],
                title=video["title"],
                view_count=video["view_count"],
                like_count=video["like_count"],
                comment_count=video["comment_count"],
                published_at=video["published_at"],
            )
            for video in recent_videos
        ]
    )
