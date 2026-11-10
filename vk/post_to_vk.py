# -*- coding: utf-8 -*-
"""Постинг контента pc-diag в VK-сообщество через VK API.

Токен и id сообщества берутся из <project>/.dev.vars:
    VK_TOKEN=...
    VK_GROUP_ID=243150004

Запуск:
    python vk/post_to_vk.py test      # один пост (закреп) — проверить права
    python vk/post_to_vk.py all       # опубликовать всё сейчас
    python vk/post_to_vk.py schedule  # разложить по дням (отложенные записи)
"""
import os
import re
import sys
import json
import time
import uuid
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

BASE = "https://api.vk.com/method/"
V = "5.199"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VK_DIR = os.path.dirname(os.path.abspath(__file__))
POSTS_MD = os.path.join(VK_DIR, "posts.md")

IMAGE_BY_POST = {
    1: "post_download.png",
    2: "post_ssd.png",
    3: "post_fan.png",
    4: "post_paste.png",
    5: "post_eventlog.png",
    6: "post_network.png",
    7: "post_case.png",
    8: "post_update.png",
    9: None,
    10: "post_month.png",
}


def load_cfg():
    path = os.path.join(ROOT, ".dev.vars")
    cfg = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            cfg[k.strip()] = v.strip()
    return cfg["VK_TOKEN"], cfg["VK_GROUP_ID"]


def api(method, params, token):
    params = dict(params)
    params["access_token"] = token
    params["v"] = V
    data = urllib.parse.urlencode(params).encode("utf-8")
    req = urllib.request.Request(BASE + method, data=data)
    with urllib.request.urlopen(req, timeout=60) as resp:
        res = json.loads(resp.read().decode("utf-8"))
    if "error" in res:
        raise RuntimeError(json.dumps(res["error"], ensure_ascii=False))
    return res["response"]


def upload_photo(token, group_id, path):
    up = api("photos.getWallUploadServer", {"group_id": group_id}, token)
    url = up["upload_url"]
    boundary = "----vk" + uuid.uuid4().hex
    with open(path, "rb") as fh:
        file_data = fh.read()
    fname = os.path.basename(path)
    body = b"".join([
        ("--" + boundary + "\r\n").encode(),
        ('Content-Disposition: form-data; name="photo"; filename="%s"\r\n' % fname).encode(),
        b"Content-Type: image/png\r\n\r\n",
        file_data,
        ("\r\n--" + boundary + "--\r\n").encode(),
    ])
    req = urllib.request.Request(
        url, data=body,
        headers={"Content-Type": "multipart/form-data; boundary=" + boundary},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        upres = json.loads(resp.read().decode("utf-8"))
    saved = api("photos.saveWallPhoto", {
        "group_id": group_id,
        "photo": upres["photo"],
        "server": upres["server"],
        "hash": upres["hash"],
    }, token)
    ph = saved[0]
    return "photo%s_%s" % (ph["owner_id"], ph["id"])

def wall_post(token, group_id, message, image_path=None, publish_date=None):
    att = upload_photo(token, group_id, image_path) if image_path else None
    params = {"owner_id": -int(group_id), "from_group": 1, "message": message}
    if att:
        params["attachments"] = att
    if publish_date:
        params["publish_date"] = int(publish_date)
    return api("wall.post", params, token)


def parse_posts():
    sections, cur = [], None
    with open(POSTS_MD, encoding="utf-8") as fh:
        for raw in fh:
            line = raw.rstrip("\n")
            if line.startswith("## "):
                if cur:
                    sections.append(cur)
                cur = {"title": line[3:].strip(), "lines": []}
            elif cur is not None:
                cur["lines"].append(line)
    if cur:
        sections.append(cur)
    out = []
    for sec in sections:
        title = sec["title"]
        text_lines = []
        for ln in sec["lines"]:
            s = ln.strip()
            if s.startswith(">"):
                s = s[1:].strip()
            if s == "---" or s.startswith("## "):
                continue
            text_lines.append(s)
        text = "\n".join([t for t in text_lines if t]).strip()
        if not text:
            continue
        m = re.search(r"Пост\s+(\d+)", title)
        if "Закреплённый" in title:
            out.append({"kind": "pin", "num": 0, "text": text, "image": "post_intro.png"})
        elif m:
            num = int(m.group(1))
            if num == 9:
                continue
            out.append({"kind": "post", "num": num, "text": text, "image": IMAGE_BY_POST.get(num)})
    return out


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "test"
    token, group_id = load_cfg()
    posts = parse_posts()
    if not posts:
        print("Нет постов для публикации")
        return
    if mode == "test":
        p = posts[0]
        res = wall_post(token, group_id, p["text"], os.path.join(VK_DIR, p["image"]))
        print("OK post_id:", res["post_id"])
        try:
            api("wall.pin", {"owner_id": -int(group_id), "post_id": res["post_id"]}, token)
            print("OK pinned")
        except Exception as exc:  # noqa: BLE001
            print("pin skip:", exc)
        return
    if mode == "all":
        for p in posts:
            img = os.path.join(VK_DIR, p["image"]) if p["image"] else None
            res = wall_post(token, group_id, p["text"], img)
            print("POST", p["kind"], p["num"], "->", res["post_id"])
            time.sleep(2)
        return
    if mode == "schedule":
        base = datetime.now().replace(hour=12, minute=0, second=0, microsecond=0)
        for i, p in enumerate(posts):
            dt = base + timedelta(days=i * 2)
            img = os.path.join(VK_DIR, p["image"]) if p["image"] else None
            res = wall_post(token, group_id, p["text"], img, int(dt.timestamp()))
            print("SCHEDULED", p["kind"], p["num"], "at", dt.strftime("%Y-%m-%d %H:%M"))
            time.sleep(2)
        return
    print("mode: test | all | schedule")


if __name__ == "__main__":
    main()
