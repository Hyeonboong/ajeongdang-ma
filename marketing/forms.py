from django import forms

from .models import Campaign, MarketingSetting, TrackingLink, YouTubeChannel


class YouTubeChannelChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        main_content = obj.main_content or "주요 콘텐츠 미입력"
        return f"{obj.channel_name or obj.channel_url} - {main_content}"


class CampaignAnalysisChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        campaign_name = obj.name or f"캠페인 #{obj.pk}"
        if obj.youtube_channel:
            main_content = obj.youtube_channel.main_content or "주요 콘텐츠 미입력"
            return f"{campaign_name} - {obj.youtube_channel.channel_name} - {main_content}"
        return campaign_name


class CampaignForm(forms.ModelForm):
    AD_TYPE_CHOICES = [
        ("브랜디드 콘텐츠", "브랜디드 콘텐츠"),
        ("PPL", "PPL"),
        ("쇼츠 협찬", "쇼츠 협찬"),
        ("커뮤니티 게시글", "커뮤니티 게시글"),
        ("라이브 방송 협찬", "라이브 방송 협찬"),
        ("기타", "기타"),
    ]
    STATUS_CHOICES = [
        ("컨택예정", "컨택예정"),
        ("컨택중", "컨택중"),
        ("진행중", "진행중"),
        ("보류", "보류"),
        ("완료", "완료"),
        ("컨택실패", "컨택실패"),
    ]

    youtube_channel = YouTubeChannelChoiceField(
        queryset=YouTubeChannel.objects.none(),
        required=False,
        empty_label="선택 안 함",
        label="협찬 유튜브 채널",
    )
    ad_type = forms.ChoiceField(label="광고 유형", choices=AD_TYPE_CHOICES)
    status = forms.ChoiceField(label="캠페인 상태", choices=STATUS_CHOICES)
    cost = forms.IntegerField(label="광고비", min_value=0, initial=0)

    class Meta:
        model = Campaign
        fields = [
            "name",
            "service_type",
            "ad_type",
            "status",
            "youtube_channel",
            "cost",
            "start_date",
            "end_date",
            "memo",
        ]
        labels = {
            "name": "캠페인명",
            "service_type": "상품/서비스",
            "ad_type": "광고 유형",
            "status": "캠페인 상태",
            "youtube_channel": "협찬 유튜브 채널",
            "cost": "광고비",
            "start_date": "시작일",
            "end_date": "종료일",
            "memo": "메모",
        }
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
            "memo": forms.Textarea(attrs={"rows": 4, "placeholder": "협찬 검토 사유, 기대 효과, 협상 내용 등을 간단히 기록하세요."}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["youtube_channel"].queryset = YouTubeChannel.objects.order_by("channel_name")
        if not self.is_bound and not (self.instance and self.instance.pk):
            self.fields["ad_type"].initial = "브랜디드 콘텐츠"
            self.fields["status"].initial = "컨택예정"
        if self.instance and self.instance.pk:
            self.initial["cost"] = int(self.instance.cost / 10000)
        _apply_bootstrap_classes(self.fields)

    def clean_cost(self):
        cost_manwon = self.cleaned_data.get("cost") or 0
        return cost_manwon * 10000

    def save(self, commit=True):
        campaign = super().save(commit=False)
        campaign.channel = "유튜브 협찬"
        campaign.objective = ""
        if commit:
            campaign.save()
            self.save_m2m()
        return campaign


class TrackingLinkForm(forms.ModelForm):
    class Meta:
        model = TrackingLink
        fields = ["name", "destination_url"]
        labels = {
            "name": "등록 링크명",
            "destination_url": "추적할 랜딩 URL",
        }
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "예: 김진짜 영상 고정댓글 링크"}),
            "destination_url": forms.URLInput(attrs={"placeholder": "예: https://www.example.com/landing 또는 기존 UTM 링크"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["destination_url"].required = True
        _apply_bootstrap_classes(self.fields)


class YoutubeAnalyzeForm(forms.Form):
    campaign = forms.ModelChoiceField(
        label="연결할 캠페인",
        queryset=Campaign.objects.all(),
        required=True,
        empty_label="캠페인을 선택하세요",
    )
    consultation_count = forms.IntegerField(label="내부 상담수", min_value=0, required=False)
    contract_count = forms.IntegerField(label="내부 가입수", min_value=0, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_bootstrap_classes(self.fields)


class YouTubeChannelAnalysisForm(forms.Form):
    campaign = CampaignAnalysisChoiceField(
        label="캠페인",
        queryset=Campaign.objects.none(),
        empty_label="캠페인을 선택하세요",
    )
    expected_paid_amount = forms.IntegerField(label="예상 협찬비", min_value=0)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["campaign"].queryset = (
            Campaign.objects.select_related("youtube_channel")
            .filter(youtube_channel__isnull=False)
            .order_by("-created_at", "-id")
        )
        _apply_bootstrap_classes(self.fields)

    def clean_campaign(self):
        campaign = self.cleaned_data["campaign"]
        if not campaign.youtube_channel:
            raise forms.ValidationError("협찬 유튜브 채널이 연결된 캠페인만 분석할 수 있습니다.")
        if not campaign.youtube_channel.channel_url:
            raise forms.ValidationError("선택한 캠페인의 유튜브 채널 URL이 비어 있습니다.")
        return campaign

    def clean_expected_paid_amount(self):
        paid_amount_manwon = self.cleaned_data.get("expected_paid_amount") or 0
        return paid_amount_manwon * 10000


class YouTubeChannelForm(forms.ModelForm):
    class Meta:
        model = YouTubeChannel
        fields = ["channel_url", "channel_name", "main_content"]
        labels = {
            "channel_url": "유튜브 채널 링크",
            "channel_name": "채널명",
            "main_content": "주요 콘텐츠",
        }
        help_texts = {
            "channel_url": "예: https://www.youtube.com/@handle 또는 https://www.youtube.com/channel/CHANNEL_ID",
            "channel_name": "직접 입력하면 API 채널명보다 우선 저장됩니다.",
            "main_content": "예: 인터넷/TV 비교, 생활비 절약, 이사 체크리스트",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_bootstrap_classes(self.fields)


class MarketingSettingForm(forms.ModelForm):
    class Meta:
        model = MarketingSetting
        fields = ["good_contract_cost", "cpv_good_max", "cpv_normal_max", "cpv_review_max"]
        labels = {
            "good_contract_cost": "가입당 비용 효율 좋음 기준",
            "cpv_good_max": "조회당 비용 효율 좋음 기준",
            "cpv_normal_max": "조회당 비용 보통 기준",
            "cpv_review_max": "조회당 비용 단가 검토 기준",
        }
        help_texts = {
            "good_contract_cost": "가입당 비용이 이 금액 이하이면 효율 좋은 캠페인으로 판단합니다.",
            "cpv_good_max": "조회당 비용이 이 금액 이하이면 효율 좋음으로 표시합니다.",
            "cpv_normal_max": "조회당 비용이 이 금액 이하이면 보통으로 표시합니다.",
            "cpv_review_max": "조회당 비용이 이 금액 이하이면 단가 검토 필요로 표시합니다. 초과하면 비용 부담 높음입니다.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_bootstrap_classes(self.fields)

    def clean(self):
        cleaned_data = super().clean()
        cpv_good_max = cleaned_data.get("cpv_good_max")
        cpv_normal_max = cleaned_data.get("cpv_normal_max")
        cpv_review_max = cleaned_data.get("cpv_review_max")
        if (
            cpv_good_max is not None
            and cpv_normal_max is not None
            and cpv_review_max is not None
            and not (cpv_good_max <= cpv_normal_max <= cpv_review_max)
        ):
            raise forms.ValidationError("조회당 비용 기준은 효율 좋음, 보통, 단가 검토 순서로 커져야 합니다.")
        return cleaned_data


def _apply_bootstrap_classes(fields):
    for field in fields.values():
        css_class = "form-select" if isinstance(field.widget, forms.Select) else "form-control"
        existing = field.widget.attrs.get("class", "")
        field.widget.attrs["class"] = f"{existing} {css_class}".strip()
