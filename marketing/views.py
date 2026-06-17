from django.contrib import messages
from django.db.models import Avg, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import (
    CSVUploadForm,
    CampaignForm,
    TrackingLinkForm,
    YouTubeChannelAnalysisForm,
    YouTubeChannelForm,
    YoutubeAnalyzeForm,
)
from .models import (
    Campaign,
    CampaignPerformance,
    ConversionEvent,
    TrackingLink,
    YouTubeChannel,
    YouTubeChannelAnalysis,
    YouTubeInfluencerAnalysis,
    YouTubeRecentVideo,
    safe_divide,
)
from .services.youtube_service import (
    get_channel_analysis_metrics,
    get_channel_recent_video_metrics,
    get_video_metrics,
)


CSV_COLUMNS = [
    "campaign_name",
    "channel",
    "ad_type",
    "cost",
    "ad_copy",
    "impressions",
    "clicks",
    "consultations",
    "contracts",
    "date",
]


def dashboard(request):
    campaigns = list(Campaign.objects.prefetch_related("performances").all())
    performance_totals = CampaignPerformance.objects.aggregate(
        impressions=Sum("impressions"),
        clicks=Sum("clicks"),
        consultations=Sum("consultations"),
        contracts=Sum("contracts"),
        avg_cost_per_consultation=Avg("cost_per_consultation"),
        avg_cost_per_contract=Avg("cost_per_contract"),
    )
    total_cost = sum(campaign.cost for campaign in campaigns)
    campaign_efficiencies = [campaign for campaign in campaigns if campaign.total_contracts > 0]
    efficient_campaigns = sorted(campaign_efficiencies, key=lambda campaign: campaign.cost_per_contract)[:5]
    inefficient_campaigns = sorted(campaign_efficiencies, key=lambda campaign: campaign.cost_per_contract, reverse=True)[:5]

    channel_costs = {}
    for campaign in campaigns:
        channel = campaign.channel or "미지정"
        channel_costs[channel] = channel_costs.get(channel, 0) + campaign.cost

    campaign_cpa_data = sorted(campaign_efficiencies, key=lambda campaign: campaign.cost_per_contract)

    context = {
        "total_cost": total_cost,
        "totals": {key: value or 0 for key, value in performance_totals.items()},
        "efficient_campaigns": efficient_campaigns,
        "inefficient_campaigns": inefficient_campaigns,
        "channel_labels": list(channel_costs.keys()),
        "channel_costs": list(channel_costs.values()),
        "campaign_cpa_labels": [campaign.name for campaign in campaign_cpa_data],
        "campaign_cpa_values": [campaign.cost_per_contract for campaign in campaign_cpa_data],
    }
    return render(request, "marketing/dashboard.html", context)


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
        Campaign.objects.prefetch_related("performances", "tracking_links__events"),
        pk=pk,
    )
    performances = campaign.performances.all()
    tracking_links = campaign.tracking_links.all()
    summary = performances.aggregate(
        total_impressions=Sum("impressions"),
        total_clicks=Sum("clicks"),
        total_consultations=Sum("consultations"),
        total_contracts=Sum("contracts"),
        avg_ctr=Avg("ctr"),
        avg_consultation_rate=Avg("consultation_rate"),
        avg_contract_rate=Avg("contract_rate"),
        avg_cost_per_consultation=Avg("cost_per_consultation"),
        avg_cost_per_contract=Avg("cost_per_contract"),
    )
    tracking_summary = {
        "clicks": sum(link.click_count for link in tracking_links),
        "consultations": sum(link.consultation_count for link in tracking_links),
        "contracts": sum(link.contract_count for link in tracking_links),
    }
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
    tracking_summary["cost_per_consultation"] = safe_divide(campaign.cost, tracking_summary["consultations"])
    tracking_summary["cost_per_contract"] = safe_divide(campaign.cost, tracking_summary["contracts"])
    return render(
        request,
        "marketing/campaign_detail.html",
        {
            "campaign": campaign,
            "performances": performances,
            "summary": {key: value or 0 for key, value in summary.items()},
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


def performance_upload(request):
    if request.method == "POST":
        form = CSVUploadForm(request.POST, request.FILES)
        if form.is_valid():
            created_count, errors = _import_performance_csv(form.cleaned_data["csv_file"])
            if errors:
                for error in errors[:5]:
                    messages.error(request, error)
                messages.error(request, "CSV 업로드 중 오류가 발생했습니다.")
            else:
                messages.success(request, f"{created_count}건의 광고 성과 데이터가 업로드되었습니다.")
                return redirect("marketing:dashboard")
    else:
        form = CSVUploadForm()
    return render(request, "marketing/performance_upload.html", {"form": form, "sample_columns": CSV_COLUMNS})


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

            recent_videos = metrics.get("recent_videos", [])
            channel.channel_id = metrics["channel_id"]
            channel.channel_name = manual_channel_name or metrics["channel_name"]
            channel.subscriber_count = metrics["subscriber_count"]
            channel.total_view_count = metrics["total_view_count"]
            channel.video_count = metrics["video_count"]
            channel.recent_video_count = metrics["recent_video_count"]
            channel.recent_avg_views = metrics["recent_avg_views"]
            channel.recent_median_views = metrics["recent_median_views"]
            channel.recent_min_views = metrics["recent_min_views"]
            channel.recent_max_views = metrics["recent_max_views"]
            channel.recent_avg_likes = _average([video["like_count"] for video in recent_videos])
            channel.recent_avg_comments = _average([video["comment_count"] for video in recent_videos])
            channel.save()
            messages.success(request, "유튜버 채널이 저장되었습니다.")
            return redirect("marketing:youtube_channel_detail", pk=channel.pk)
    else:
        form = YouTubeChannelForm()
    return render(request, "marketing/youtube_channel_form.html", {"form": form})


def youtube_channel_detail(request, pk):
    channel = get_object_or_404(YouTubeChannel, pk=pk)
    campaigns = channel.campaigns.order_by("-created_at", "-id")
    return render(request, "marketing/youtube_channel_detail.html", {"channel": channel, "campaigns": campaigns})


@require_POST
def youtube_channel_delete(request, pk):
    channel = get_object_or_404(YouTubeChannel, pk=pk)
    channel.delete()
    messages.success(request, "유튜버 채널이 삭제되었습니다.")
    return redirect("marketing:youtube_channel_list")


def youtube_analyze(request):
    recent_results = YouTubeInfluencerAnalysis.objects.all()[:5]
    if request.method == "POST":
        form = YoutubeAnalyzeForm(request.POST)
        if form.is_valid():
            url = form.cleaned_data["youtube_url"]
            try:
                metrics = get_video_metrics(url)
            except Exception as exc:
                messages.error(request, f"유튜브 분석 중 오류가 발생했습니다: {exc}")
                return render(request, "marketing/youtube_analyze.html", {"form": form, "recent_results": recent_results})

            analysis = YouTubeInfluencerAnalysis.objects.create(
                campaign=form.cleaned_data["campaign"],
                youtube_url=url,
                channel_name=metrics["channel_name"],
                subscriber_count=metrics["subscriber_count"],
                video_title=metrics["video_title"],
                view_count=metrics["view_count"],
                like_count=metrics["like_count"],
                comment_count=metrics["comment_count"],
                published_at=metrics["published_at"],
                paid_amount=form.cleaned_data["paid_amount"],
                consultation_count=form.cleaned_data.get("consultation_count") or 0,
                contract_count=form.cleaned_data.get("contract_count") or 0,
            )
            messages.success(request, "유튜브 협찬 광고 분석이 저장되었습니다.")
            return redirect("marketing:youtube_result", pk=analysis.pk)
    else:
        form = YoutubeAnalyzeForm()
    return render(request, "marketing/youtube_analyze.html", {"form": form, "recent_results": recent_results})


def youtube_result(request, pk):
    analysis = get_object_or_404(YouTubeInfluencerAnalysis, pk=pk)
    recent_video_metrics = None
    recent_video_error = ""

    try:
        recent_video_metrics = get_channel_recent_video_metrics(analysis.youtube_url, limit=10)
    except Exception as exc:
        recent_video_error = str(exc)

    if not analysis.consultation_count and not analysis.contract_count:
        efficiency_message = "실제 상담/가입 효과를 보려면 UTM, 추천코드, 전용 랜딩페이지 등 내부 전환 데이터 연결이 필요합니다."
    elif analysis.view_count >= 100000 and analysis.contract_count <= 3:
        efficiency_message = "브랜드 노출 효과는 있으나 가입 전환 효율은 낮습니다."
    elif analysis.cost_per_contract and analysis.cost_per_contract <= 50000:
        efficiency_message = "지급 광고비 대비 가입 전환 효율이 좋은 캠페인입니다."
    else:
        efficiency_message = "조회, 상담, 가입 데이터를 함께 보며 추가 최적화가 필요합니다."

    return render(
        request,
        "marketing/youtube_result.html",
        {
            "analysis": analysis,
            "efficiency_message": efficiency_message,
            "recent_video_metrics": recent_video_metrics,
            "recent_video_error": recent_video_error,
        },
    )


def youtube_channel_analyze(request):
    if request.method == "POST":
        form = YouTubeChannelAnalysisForm(request.POST)
        if form.is_valid():
            campaign = form.cleaned_data["campaign"]
            channel_url = campaign.youtube_channel.channel_url
            expected_paid_amount = form.cleaned_data["expected_paid_amount"]
            try:
                metrics = get_channel_analysis_metrics(channel_url, limit=10)
            except Exception as exc:
                messages.error(request, f"유튜버 단가 분석 중 오류가 발생했습니다: {exc}")
                return render(request, "marketing/youtube_channel_analyze.html", {"form": form})

            analysis = YouTubeChannelAnalysis.objects.create(
                campaign=campaign,
                channel_url=channel_url,
                channel_id=metrics["channel_id"],
                channel_name=metrics["channel_name"],
                subscriber_count=metrics["subscriber_count"],
                total_view_count=metrics["total_view_count"],
                video_count=metrics["video_count"],
                recent_video_count=metrics["recent_video_count"],
                recent_avg_views=metrics["recent_avg_views"],
                recent_median_views=metrics["recent_median_views"],
                recent_min_views=metrics["recent_min_views"],
                recent_max_views=metrics["recent_max_views"],
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
    return render(request, "marketing/youtube_channel_analyze.html", {"form": form})


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


def _import_performance_csv(uploaded_file):
    try:
        import pandas as pd
    except ImportError:
        return 0, ["pandas가 설치되어 있지 않습니다. pip install -r requirements.txt를 실행해주세요."]

    try:
        dataframe = pd.read_csv(uploaded_file)
    except Exception as exc:
        return 0, [f"CSV 파일을 읽을 수 없습니다: {exc}"]

    missing_columns = [column for column in CSV_COLUMNS if column not in dataframe.columns]
    if missing_columns:
        return 0, [f"누락된 컬럼: {', '.join(missing_columns)}"]

    created_count = 0
    errors = []
    for index, row in dataframe.iterrows():
        try:
            campaign_name = _text(row["campaign_name"])
            if not campaign_name:
                raise ValueError("campaign_name은 필수입니다.")

            performance_date = _date_value(row["date"])
            campaign, _ = Campaign.objects.get_or_create(
                name=campaign_name,
                defaults={
                    "channel": _text(row["channel"]),
                    "ad_type": _text(row["ad_type"]),
                    "cost": _int_value(row["cost"]),
                    "start_date": performance_date,
                    "end_date": performance_date,
                },
            )
            CampaignPerformance.objects.create(
                campaign=campaign,
                ad_copy=_text(row["ad_copy"]),
                impressions=_int_value(row["impressions"]),
                clicks=_int_value(row["clicks"]),
                consultations=_int_value(row["consultations"]),
                contracts=_int_value(row["contracts"]),
                date=performance_date,
            )
            created_count += 1
        except Exception as exc:
            errors.append(f"{index + 2}행: {exc}")

    return created_count, errors


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
