# Generated for the marketing_roi portfolio project.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Campaign",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120, verbose_name="캠페인명")),
                (
                    "channel",
                    models.CharField(
                        choices=[
                            ("search", "검색 광고"),
                            ("display", "디스플레이 광고"),
                            ("social", "소셜 광고"),
                            ("youtube", "유튜브"),
                            ("kakao", "카카오톡"),
                            ("other", "기타"),
                        ],
                        max_length=20,
                        verbose_name="채널",
                    ),
                ),
                ("budget", models.DecimalField(decimal_places=0, default=0, max_digits=12, verbose_name="예산")),
                ("start_date", models.DateField(verbose_name="시작일")),
                ("end_date", models.DateField(blank=True, null=True, verbose_name="종료일")),
                ("goal", models.TextField(blank=True, verbose_name="목표")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="등록일")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="수정일")),
            ],
            options={
                "verbose_name": "캠페인",
                "verbose_name_plural": "캠페인",
                "ordering": ["-start_date", "-id"],
            },
        ),
        migrations.CreateModel(
            name="YoutubeAnalysis",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("creator_name", models.CharField(max_length=100, verbose_name="유튜버명")),
                ("video_title", models.CharField(max_length=160, verbose_name="영상 제목")),
                ("video_url", models.URLField(blank=True, verbose_name="영상 URL")),
                ("sponsorship_cost", models.DecimalField(decimal_places=0, max_digits=12, verbose_name="협찬 비용")),
                ("views", models.PositiveIntegerField(verbose_name="조회수")),
                ("likes", models.PositiveIntegerField(default=0, verbose_name="좋아요 수")),
                ("comments", models.PositiveIntegerField(default=0, verbose_name="댓글 수")),
                ("consultations", models.PositiveIntegerField(default=0, verbose_name="상담 신청 수")),
                ("signups", models.PositiveIntegerField(default=0, verbose_name="가입 수")),
                ("memo", models.TextField(blank=True, verbose_name="메모")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="분석일")),
            ],
            options={
                "verbose_name": "유튜브 협찬 분석",
                "verbose_name_plural": "유튜브 협찬 분석",
                "ordering": ["-created_at", "-id"],
            },
        ),
        migrations.CreateModel(
            name="CampaignPerformance",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("date", models.DateField(verbose_name="일자")),
                ("cost", models.DecimalField(decimal_places=0, default=0, max_digits=12, verbose_name="광고비")),
                ("impressions", models.PositiveIntegerField(default=0, verbose_name="노출수")),
                ("clicks", models.PositiveIntegerField(default=0, verbose_name="클릭수")),
                ("consultations", models.PositiveIntegerField(default=0, verbose_name="상담 신청 수")),
                ("signups", models.PositiveIntegerField(default=0, verbose_name="가입 수")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="등록일")),
                (
                    "campaign",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="performances",
                        to="marketing.campaign",
                        verbose_name="캠페인",
                    ),
                ),
            ],
            options={
                "verbose_name": "캠페인 성과",
                "verbose_name_plural": "캠페인 성과",
                "ordering": ["-date", "-id"],
            },
        ),
    ]
