import uuid

from django.db import models
from django.urls import reverse


def safe_divide(numerator, denominator, multiplier=1):
    if not denominator:
        return 0
    return round((numerator / denominator) * multiplier, 2)


class Campaign(models.Model):
    OBJECTIVE_CHOICES = [
        ("브랜드 인지도", "브랜드 인지도"),
        ("상담 신청 증가", "상담 신청 증가"),
        ("가입 전환 증가", "가입 전환 증가"),
        ("이벤트 홍보", "이벤트 홍보"),
    ]
    SERVICE_TYPE_CHOICES = [
        ("인터넷", "인터넷"),
        ("인터넷+TV", "인터넷+TV"),
        ("정수기 렌탈", "정수기 렌탈"),
        ("가전 렌탈", "가전 렌탈"),
        ("휴대폰", "휴대폰"),
        ("이사", "이사"),
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

    name = models.CharField(max_length=120, default="", blank=True)
    objective = models.CharField(max_length=100, choices=OBJECTIVE_CHOICES, default="", blank=True)
    service_type = models.CharField(max_length=100, choices=SERVICE_TYPE_CHOICES, default="", blank=True)
    channel = models.CharField(max_length=50, default="", blank=True)
    ad_type = models.CharField(max_length=50, default="", blank=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default="컨택예정", blank=True)
    youtube_channel = models.ForeignKey(
        "YouTubeChannel",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="campaigns",
    )
    cost = models.PositiveIntegerField(default=0)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    memo = models.TextField(default="", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("marketing:campaign_detail", kwargs={"pk": self.pk})

    @property
    def total_cost(self):
        return self.cost

    @property
    def total_impressions(self):
        return self.performances.aggregate(total=models.Sum("impressions"))["total"] or 0

    @property
    def total_clicks(self):
        return self.performances.aggregate(total=models.Sum("clicks"))["total"] or 0

    @property
    def total_consultations(self):
        return self.performances.aggregate(total=models.Sum("consultations"))["total"] or 0

    @property
    def total_contracts(self):
        return self.performances.aggregate(total=models.Sum("contracts"))["total"] or 0

    @property
    def total_signups(self):
        return self.total_contracts

    @property
    def ctr(self):
        return safe_divide(self.total_clicks, self.total_impressions, 100)

    @property
    def consultation_rate(self):
        return safe_divide(self.total_consultations, self.total_clicks, 100)

    @property
    def contract_rate(self):
        return safe_divide(self.total_contracts, self.total_consultations, 100)

    @property
    def signup_rate(self):
        return self.contract_rate

    @property
    def cost_per_consultation(self):
        return safe_divide(self.cost, self.total_consultations)

    @property
    def cost_per_contract(self):
        return safe_divide(self.cost, self.total_contracts)

    @property
    def cost_per_signup(self):
        return self.cost_per_contract


class CampaignPerformance(models.Model):
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="performances")
    ad_copy = models.TextField(default="", blank=True)
    impressions = models.PositiveIntegerField(default=0)
    clicks = models.PositiveIntegerField(default=0)
    consultations = models.PositiveIntegerField(default=0)
    contracts = models.PositiveIntegerField(default=0)
    date = models.DateField(null=True, blank=True)
    ctr = models.FloatField(default=0)
    consultation_rate = models.FloatField(default=0)
    contract_rate = models.FloatField(default=0)
    cost_per_consultation = models.FloatField(default=0)
    cost_per_contract = models.FloatField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-id"]

    def __str__(self):
        return f"{self.campaign.name} - {self.date}"

    def save(self, *args, **kwargs):
        self.ctr = safe_divide(self.clicks, self.impressions, 100)
        self.consultation_rate = safe_divide(self.consultations, self.clicks, 100)
        self.contract_rate = safe_divide(self.contracts, self.consultations, 100)
        self.cost_per_consultation = safe_divide(self.campaign.cost, self.consultations)
        self.cost_per_contract = safe_divide(self.campaign.cost, self.contracts)
        super().save(*args, **kwargs)

    @property
    def cost(self):
        return self.campaign.cost

    @property
    def signups(self):
        return self.contracts

    @property
    def cost_per_signup(self):
        return self.cost_per_contract


class TrackingLink(models.Model):
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="tracking_links")
    name = models.CharField(max_length=120, default="", blank=True)
    code = models.SlugField(max_length=80, unique=True, default="", blank=True)
    destination_url = models.URLField(default="", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return self.name or self.code

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = uuid.uuid4().hex[:10]
        super().save(*args, **kwargs)

    @property
    def click_count(self):
        return self.events.filter(event_type=ConversionEvent.EventType.CLICK).count()

    @property
    def consultation_count(self):
        return self.events.filter(event_type=ConversionEvent.EventType.CONSULTATION).count()

    @property
    def contract_count(self):
        return self.events.filter(event_type=ConversionEvent.EventType.CONTRACT).count()

    @property
    def consultation_rate(self):
        return safe_divide(self.consultation_count, self.click_count, 100)

    @property
    def contract_rate(self):
        return safe_divide(self.contract_count, self.consultation_count, 100)

    @property
    def cost_per_consultation(self):
        return safe_divide(self.campaign.cost, self.consultation_count)

    @property
    def cost_per_contract(self):
        return safe_divide(self.campaign.cost, self.contract_count)


class ConversionEvent(models.Model):
    class EventType(models.TextChoices):
        CLICK = "click", "클릭"
        CONSULTATION = "consultation", "상담 신청"
        CONTRACT = "contract", "가입"

    tracking_link = models.ForeignKey(TrackingLink, on_delete=models.CASCADE, related_name="events")
    event_type = models.CharField(max_length=30, choices=EventType.choices, default=EventType.CLICK)
    memo = models.CharField(max_length=200, default="", blank=True)
    occurred_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-occurred_at", "-id"]

    def __str__(self):
        return f"{self.tracking_link} - {self.get_event_type_display()}"


class YouTubeChannel(models.Model):
    channel_url = models.URLField(default="", blank=True)
    channel_id = models.CharField(max_length=120, default="", blank=True)
    channel_name = models.CharField(max_length=120, default="", blank=True)
    main_content = models.CharField(max_length=200, default="", blank=True)
    subscriber_count = models.PositiveIntegerField(default=0)
    total_view_count = models.PositiveIntegerField(default=0)
    video_count = models.PositiveIntegerField(default=0)
    recent_video_count = models.PositiveIntegerField(default=0)
    recent_avg_views = models.FloatField(default=0)
    recent_median_views = models.FloatField(default=0)
    recent_min_views = models.PositiveIntegerField(default=0)
    recent_max_views = models.PositiveIntegerField(default=0)
    recent_avg_likes = models.FloatField(default=0)
    recent_avg_comments = models.FloatField(default=0)
    subscriber_view_rate = models.FloatField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["channel_name", "-id"]

    def __str__(self):
        if self.channel_name and self.main_content:
            return f"{self.channel_name} - {self.main_content}"
        return self.channel_name or self.channel_url

    def save(self, *args, **kwargs):
        self.subscriber_view_rate = safe_divide(self.recent_avg_views, self.subscriber_count, 100)
        super().save(*args, **kwargs)


class YouTubeInfluencerAnalysis(models.Model):
    campaign = models.ForeignKey(Campaign, on_delete=models.SET_NULL, null=True, blank=True, related_name="youtube_analyses")
    youtube_url = models.URLField(default="", blank=True)
    channel_name = models.CharField(max_length=100, default="", blank=True)
    subscriber_count = models.PositiveIntegerField(default=0)
    video_title = models.CharField(max_length=160, default="", blank=True)
    view_count = models.PositiveIntegerField(default=0)
    like_count = models.PositiveIntegerField(default=0)
    comment_count = models.PositiveIntegerField(default=0)
    published_at = models.DateField(null=True, blank=True)
    paid_amount = models.PositiveIntegerField(default=0)
    cost_per_view = models.FloatField(default=0)
    consultation_count = models.PositiveIntegerField(default=0)
    contract_count = models.PositiveIntegerField(default=0)
    cost_per_consultation = models.FloatField(default=0)
    cost_per_contract = models.FloatField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.channel_name} - {self.video_title}"

    def save(self, *args, **kwargs):
        self.cost_per_view = safe_divide(self.paid_amount, self.view_count)
        self.cost_per_consultation = safe_divide(self.paid_amount, self.consultation_count)
        self.cost_per_contract = safe_divide(self.paid_amount, self.contract_count)
        super().save(*args, **kwargs)

    @property
    def creator_name(self):
        return self.channel_name

    @property
    def video_url(self):
        return self.youtube_url

    @property
    def sponsorship_cost(self):
        return self.paid_amount

    @property
    def views(self):
        return self.view_count

    @property
    def likes(self):
        return self.like_count

    @property
    def comments(self):
        return self.comment_count

    @property
    def consultations(self):
        return self.consultation_count

    @property
    def signups(self):
        return self.contract_count

    @property
    def cost_per_signup(self):
        return self.cost_per_contract

    @property
    def consultation_rate(self):
        return safe_divide(self.consultation_count, self.view_count, 100)

    @property
    def signup_rate(self):
        return safe_divide(self.contract_count, self.consultation_count, 100)


class YouTubeChannelAnalysis(models.Model):
    campaign = models.ForeignKey(
        Campaign,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="channel_analyses",
    )
    channel_url = models.URLField(default="", blank=True)
    channel_id = models.CharField(max_length=120, default="", blank=True)
    channel_name = models.CharField(max_length=120, default="", blank=True)
    subscriber_count = models.PositiveIntegerField(default=0)
    total_view_count = models.PositiveIntegerField(default=0)
    video_count = models.PositiveIntegerField(default=0)
    recent_video_count = models.PositiveIntegerField(default=0)
    recent_avg_views = models.FloatField(default=0)
    recent_median_views = models.FloatField(default=0)
    recent_min_views = models.PositiveIntegerField(default=0)
    recent_max_views = models.PositiveIntegerField(default=0)
    subscriber_view_rate = models.FloatField(default=0)
    expected_paid_amount = models.PositiveIntegerField(default=0)
    avg_cost_per_view = models.FloatField(default=0)
    median_cost_per_view = models.FloatField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return self.channel_name or self.channel_url

    def save(self, *args, **kwargs):
        self.subscriber_view_rate = safe_divide(self.recent_avg_views, self.subscriber_count, 100)
        self.avg_cost_per_view = safe_divide(self.expected_paid_amount, self.recent_avg_views)
        self.median_cost_per_view = safe_divide(self.expected_paid_amount, self.recent_median_views)
        super().save(*args, **kwargs)


class YouTubeRecentVideo(models.Model):
    analysis = models.ForeignKey(YouTubeChannelAnalysis, on_delete=models.CASCADE, related_name="recent_videos")
    video_id = models.CharField(max_length=50, default="", blank=True)
    title = models.CharField(max_length=200, default="", blank=True)
    view_count = models.PositiveIntegerField(default=0)
    like_count = models.PositiveIntegerField(default=0)
    comment_count = models.PositiveIntegerField(default=0)
    published_at = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["-published_at", "-id"]

    def __str__(self):
        return self.title or self.video_id
