import re
from urllib.parse import urljoin

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
    """공지사항 목록 페이지를 읽어서 게시글 레코드 목록을 반환한다.

    각 레코드: id(articleNo), title, category, date, url
    """
    resp = requests.get(URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
    resp.encoding = "utf-8"
    soup = BeautifulSoup(resp.text, "html.parser")

    notices = []
    # 실제 게시판 마크업: ul.board-list-wrap > li 하나가 게시글 한 건
    for li in soup.select("ul.board-list-wrap > li"):
        link = li.select_one("dt.board-list-content-title a[href*='mode=view']")
        if not link:
            continue

        match = re.search(r"articleNo=(\d+)", link.get("href", ""))
        if not match:
            continue

        category_tag = li.select_one(".c-board-list-category")
        # dd 안의 li 순서: [공지/게시글번호, 작성자, 날짜, 조회수]
        info_items = li.select("dd.board-list-content-info li")

        notices.append({
            "id": int(match.group(1)),
            "title": link.get_text(strip=True),
            "category": category_tag.get_text(strip=True) if category_tag else None,
            "date": info_items[2].get_text(strip=True) if len(info_items) > 2 else None,
            "url": urljoin(URL, link["href"]),
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


def save_notice_record(db, notice: dict) -> None:
    """새로 발견한 공지 레코드 전체(title, category, date, url)를
    notices 컬렉션에 히스토리로 남긴다. 문서 이름은 articleNo."""
    db.collection("notices").document(str(notice["id"])).set(notice)


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
        label = f"[{notice['category']}] {notice['title']}" if notice["category"] else notice["title"]
        send_push(label)
        save_notice_record(db, notice)

    if notices:
        save_last_seen_id(db, max(n["id"] for n in notices))


if __name__ == "__main__":
    main()