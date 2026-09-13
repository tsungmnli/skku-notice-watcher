# skku-notice-watcher

성균관대학교 공지사항 게시판을 주기적으로 확인해서
새 글이 올라오면 FCM으로 푸시 알림을 보내는 스크립트입니다.

## 준비 과정

1. [Firebase 콘솔](https://console.firebase.google.com)에서 프로젝트 생성
   (skkunoticenow 앱에서 쓸 프로젝트와 **동일한 프로젝트**를 사용하세요)
2. 해당 프로젝트에서 Cloud Messaging, Firestore 사용 설정
3. 프로젝트 설정 > 서비스 계정 > "새 비공개 키 생성"으로 JSON 키 파일 다운로드
4. 이 저장소의 GitHub 설정 > Secrets and variables > Actions 에서
   `FIREBASE_KEY`라는 이름으로 새 시크릿을 만들고, 3번에서 받은 JSON 파일 내용을
   그대로 붙여넣기
5. 앱(skkunoticenow) 쪽에서는 같은 Firebase 프로젝트에 연결하고
   `skku_notices` 토픽을 구독하도록 설정

## 동작 방식

- `.github/workflows/check.yml`이 10분마다 `check_notices.py`를 자동 실행합니다.
- 스크립트는 공지사항 페이지를 읽어서 게시글 고유 번호(articleNo)를 비교합니다.
- Firestore에 저장된 "마지막으로 본 번호"보다 큰 글이 있으면,
  그 제목으로 FCM 푸시를 `skku_notices` 토픽에 보냅니다.
- 보낸 뒤에는 Firestore에 최신 번호를 다시 저장합니다.

## 로컬에서 테스트해보기

```bash
pip install -r requirements.txt
# firebase-key.json 파일을 이 폴더에 직접 놓고
python check_notices.py
```

## 확인 주기 조정

`.github/workflows/check.yml`의 cron 표현식을 바꾸면 됩니다.
예: `*/30 * * * *` 는 30분마다, `*/5 * * * *` 는 5분마다.

GitHub Actions의 스케줄 실행은 정확히 그 시각에 딱 맞춰 도는 게 아니라
몇 분 정도 밀릴 수 있어요. 공지사항 알림 정도는 문제없는 수준입니다.
