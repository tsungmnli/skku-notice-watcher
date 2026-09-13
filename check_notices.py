import re

import requests
from bs4 import BeautifulSoup

import firebase_admin
from firebase_admin import credentials, firestore, messaging

URL = "https://www.skku.edu/skku/campus/skk_comm/notice01.do"
TOPIC = "skku_notices"
STATE_COLLECTION = "watcher_state"
STATE_DOC = "skku_notice"


def init_firebase():
    """Firebase 앱을 초기화하고 Firestore 클라이언트를 반환한다."""
    cred = credentials.Certificate("firebase-key.json")
    firebase_admin.initialize_app(cred)
    return firestore.client()


def get_latest_notices():
    """공지사항 목록 페이지를 읽어서 [{id, title}, ...] 형태로 반환한다."""
    resp = requests.get(URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
    resp.encoding = "utf-8"
    soup = BeautifulSoup(resp.text, "html.parser")

    notices = []
    for a in soup.select("a[href*='mode=view']"):
        match = re.search(r"articleNo=(\d+)", a.get("href", ""))
        if match:
            notices.append({
                "id": int(match.group(1)),
                "title": a.get_text(strip=True),
            })
    return notices


def get_last_seen_id(db) -> int:
    """마지막으로 확인했던 게시글 번호를 Firestore에서 읽어온다. 없으면 0."""
    doc = db.collection(STATE_COLLECTION).document(STATE_DOC).get()
    if doc.exists:
        return doc.to_dict().get("last_id", 0)
    return 0


def save_last_seen_id(db, article_id: int) -> None:
    """가장 최신 게시글 번호를 Firestore에 저장한다."""
    db.collection(STATE_COLLECTION).document(STATE_DOC).set({"last_id": article_id})


def send_push(title: str) -> None:
    """FCM 토픽 구독자 전체에게 알림 메시지를 보낸다."""
    message = messaging.Message(
        notification=messaging.Notification(title="새 공지사항", body=title),
        topic=TOPIC,
    )
    messaging.send(message)


def main():
    db = init_firebase()
    last_id = get_last_seen_id(db)

    notices = get_latest_notices()
    new_ones = sorted(
        [n for n in notices if n["id"] > last_id],
        key=lambda n: n["id"],
    )

    for notice in new_ones:
        send_push(notice["title"])

    if notices:
        save_last_seen_id(db, max(n["id"] for n in notices))


if __name__ == "__main__":
    main()