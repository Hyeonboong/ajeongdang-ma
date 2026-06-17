# Marketing ROI Portfolio

Django 기반의 마케팅 비용 대비 전환 효율 분석 및 유튜버 협찬 성과 분석 시스템입니다.

## 주요 기능

- 캠페인 등록 및 목록/상세 조회
- CSV 광고 성과 업로드
- 광고비, 노출수, 클릭수, 상담 신청 수, 가입 수 기반 전환 효율 계산
- 대시보드 KPI, 효율 TOP 5, 비효율 TOP 5
- YouTube Data API v3 기반 유튜브 영상 지표 분석
- 협찬 전 유튜버 채널 단가 사전 분석
- `YOUTUBE_API_KEY`가 없을 때 mock 데이터 fallback
- Bootstrap 기반 Django Template UI
- Chart.js 시각화

## 실행 방법

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

## YouTube API 키 설정

실제 YouTube Data API v3를 사용하려면 Google Cloud Console에서 YouTube Data API v3를 사용 설정하고 API 키를 발급한 뒤 `YOUTUBE_API_KEY` 환경변수에 넣습니다.

CMD:

```cmd
set YOUTUBE_API_KEY=발급받은_API_KEY
python manage.py runserver
```

PowerShell:

```powershell
$env:YOUTUBE_API_KEY="발급받은_API_KEY"
python manage.py runserver
```

`YOUTUBE_API_KEY`가 없으면 mock 데이터로 동작합니다. API 키가 있는데 호출이 실패하면 mock으로 넘어가지 않고 화면에 오류 메시지를 표시합니다.

## URL

- `/` : 대시보드
- `/campaigns/` : 캠페인 목록
- `/campaigns/create/` : 캠페인 등록
- `/campaigns/<id>/` : 캠페인 상세
- `/performances/upload/` : CSV 업로드
- `/youtube/analyze/` : 유튜브 분석
- `/youtube/results/<id>/` : 유튜브 분석 결과
- `/youtube/channel-analyze/` : 유튜버 채널 단가 사전 분석
- `/youtube/channel-results/<id>/` : 유튜버 채널 단가 분석 결과

## CSV 형식

```csv
campaign_name,channel,ad_type,cost,ad_copy,impressions,clicks,consultations,contracts,date
인터넷 가입 검색광고,네이버,검색광고,500000,"인터넷 가입 혜택 비교",120000,3400,160,38,2026-06-10
```
