#!/usr/bin/env python3
"""알리오 채용정보를 받아 public/data/jobs.json 으로 저장한다. (표준 라이브러리만 사용)
사용: python3 scripts/fetch_alio.py            # 알리오에서 최근 30일치 받기
      python3 scripts/fetch_alio.py --file x.csv  # 이미 받은 CSV로 변환만 테스트
"""
import argparse, csv, io, json, sys, urllib.request, urllib.error
from datetime import datetime, timedelta, timezone

URL = "https://www.alio.go.kr/information/downExcelRecruitList.json"
OUT = "public/data/jobs.json"
DAYS = 30
KST = timezone(timedelta(hours=9))
NEED = ["제목", "기관명", "표준직무(NCS)", "고용형태", "공고기간", "원문URL", "등록일", "마감일"]


def download(days):
    now = datetime.now(KST)
    payload = {
        "detailcodeValueArr": [], "locationValueArr": [], "worktypeValueArr": [],
        "eduValueArr": [], "areaValueArr": [], "carrerValueArr": [],
        "apba_type": "", "apba_id": "", "replacement": "", "title": "",
        "s_date": (now - timedelta(days=days)).strftime("%Y.%m.%d"),
        "e_date": now.strftime("%Y.%m.%d"),
        "ing": "", "order": "IDATE", "pageNo": 1,
    }
    req = urllib.request.Request(
        URL, data=json.dumps(payload).encode("utf-8"), method="POST",
        headers={
            "Content-Type": "application/json;charset=UTF-8",
            "User-Agent": "Mozilla/5.0 (personal job-list updater, once a day)",
            "Referer": "https://www.alio.go.kr/information/informationRecruitList.do",
            "Accept": "*/*",
        })
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def decode(raw):
    for enc in ("utf-8-sig", "cp949"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            pass
    raise SystemExit("인코딩을 알 수 없음")


def convert(text):
    rows = list(csv.DictReader(io.StringIO(text)))
    if not rows or any(k not in rows[0] for k in NEED):
        raise SystemExit("CSV 형식이 예상과 다름. 앞부분: " + text[:200].replace("\n", " "))
    jobs = []
    for r in rows:
        jobs.append({
            "title": r["제목"].strip(),
            "org": r["기관명"].strip(),
            "ncs": [x.strip() for x in r["표준직무(NCS)"].split("/") if x.strip()],
            "types": [x.strip() for x in r["고용형태"].split("/") if x.strip()],
            "hireKind": r.get("채용구분", "").strip(),
            "period": r["공고기간"].strip(),
            "place": r.get("근무지", "").strip(),
            "count": r.get("채용인원", "").strip(),
            "url": r["원문URL"].strip(),
            "start": r["등록일"].replace(".", "-").strip(),
            "end": r["마감일"].replace(".", "-").strip(),
        })
    return jobs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file")
    ap.add_argument("--days", type=int, default=DAYS)
    a = ap.parse_args()
    try:
        raw = open(a.file, "rb").read() if a.file else download(a.days)
    except urllib.error.HTTPError as e:
        raise SystemExit(f"요청 실패: HTTP {e.code} (기존 데이터는 그대로 둠)")
    except Exception as e:
        raise SystemExit(f"요청 실패: {e} (기존 데이터는 그대로 둠)")
    jobs = convert(decode(raw))
    if len(jobs) < 10:  # 비정상적으로 적으면 덮어쓰지 않음
        raise SystemExit(f"공고가 {len(jobs)}건뿐이라 저장 안 함")
    out = {"updatedAt": datetime.now(KST).isoformat(timespec="minutes"),
           "source": "알리오(ALIO) 공공기관 채용정보", "count": len(jobs), "jobs": jobs}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    print(f"저장 완료: {len(jobs)}건 → {OUT}")


if __name__ == "__main__":
    main()
