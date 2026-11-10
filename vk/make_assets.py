# -*- coding: utf-8 -*-
"""Генерация визуалов для VK-сообщества pc-diag (обложка, аватар, картинки постов)."""
import os
from PIL import Image, ImageDraw, ImageFont

OUT = os.path.dirname(os.path.abspath(__file__))
DARK = (18, 22, 15)
DARK2 = (27, 33, 26)
CARD = (27, 33, 26)
GREEN = (124, 194, 74)
WHITE = (255, 255, 255)
MUTED = (163, 173, 158)

F_BOLD = "C:/Windows/Fonts/segoeuib.ttf"
F_SEMI = "C:/Windows/Fonts/seguisb.ttf"
F_REG = "C:/Windows/Fonts/segoeui.ttf"


def font(path, size):
    return ImageFont.truetype(path, size)


def gradient(w, h, c1, c2, horizontal=True):
    base = Image.new("RGB", (w, h), c1)
    d = ImageDraw.Draw(base)
    if horizontal:
        for x in range(w):
            t = x / max(1, w - 1)
            col = tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))
            d.line([(x, 0), (x, h)], fill=col)
    else:
        for y in range(h):
            t = y / max(1, h - 1)
            col = tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))
            d.line([(0, y), (w, y)], fill=col)
    return base


def dashboard(d, x, y, w, h, color):
    d.rounded_rectangle([x, y, x + w, y + h], radius=14, outline=color, width=3)
    for i in range(3):
        d.ellipse([x + 16 + i * 15, y + 14, x + 24 + i * 15, y + 22], fill=color)
    bx, by, bw = x + 22, y + 54, w - 44
    d.line([(bx, by + 24), (bx + bw, by + 24)], fill=color, width=2)
    for i, hh in enumerate([26, 44, 16, 34]):
        d.rectangle([bx + i * 26, by + 70 - hh, bx + i * 26 + 14, by + 70], fill=color)
    pts = [(bx, by + 108), (bx + bw * 0.3, by + 84), (bx + bw * 0.6, by + 100), (bx + bw, by + 66)]
    d.line(pts, fill=color, width=3)


def make_cover():
    w, h = 1590, 400
    img = gradient(w, h, DARK, DARK2, horizontal=True)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 12, h], fill=GREEN)
    d.text((60, 62), "pc-diag", font=font(F_BOLD, 88), fill=WHITE)
    d.text((64, 178), "Диагностика Windows за 60 секунд", font=font(F_SEMI, 32), fill=GREEN)
    d.text((64, 232), "SMART · Event Log · Сеть · Службы · Автозагрузка", font=font(F_REG, 21), fill=MUTED)
    d.text((64, 322), "pc-diag.ru  ·  бесплатно  ·  portable", font=font(F_REG, 19), fill=MUTED)
    dashboard(d, 1180, 96, 340, 210, GREEN)
    img.save(os.path.join(OUT, "cover.png"))


def make_avatar():
    s = 400
    img = gradient(s, s, DARK, DARK2, horizontal=False)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([20, 20, 380, 380], radius=96, fill=CARD, outline=GREEN, width=6)
    d.text((200, 172), "pd", font=font(F_BOLD, 156), fill=WHITE, anchor="mm")
    d.text((200, 292), "pc-diag", font=font(F_SEMI, 34), fill=GREEN, anchor="mm")
    img.save(os.path.join(OUT, "avatar.png"))


def make_post(name, title, subtitle):
    w, h = 1080, 1080
    img = gradient(w, h, DARK, DARK2, horizontal=False)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 16, h], fill=GREEN)
    d.text((70, 96), "pc-diag", font=font(F_BOLD, 56), fill=GREEN)
    tf = font(F_BOLD, 76)
    words = title.split()
    lines, cur = [], ""
    for wd in words:
        test = (cur + " " + wd).strip()
        if d.textlength(test, font=tf) <= w - 140:
            cur = test
        else:
            lines.append(cur)
            cur = wd
    if cur:
        lines.append(cur)
    y = 320
    for ln in lines:
        d.text((70, y), ln, font=tf, fill=WHITE)
        y += 94
    d.text((70, y + 24), subtitle, font=font(F_SEMI, 36), fill=MUTED)
    d.rectangle([70, h - 168, w - 70, h - 160], fill=GREEN)
    d.text((70, h - 128), "pc-diag.ru  ·  бесплатно", font=font(F_SEMI, 36), fill=GREEN)
    img.save(os.path.join(OUT, name))


def main():
    make_cover()
    make_avatar()
    make_post("post_intro.png", "Что такое pc-diag?", "SMART · Event Log · Сеть · Службы")
    make_post("post_ssd.png", "Проверь износ SSD за 60 секунд", "SMART · Wear · Температура · Ресурс")
    make_post("post_fan.png", "Почему шумит вентилятор?", "Пыль · Термопаста · Перегрев")
    make_post("post_paste.png", "Когда менять термопасту?", "Теплопроводность · Модели · Нанесение")
    make_post("post_eventlog.png", "Ошибки Windows: что важно?", "Event Log за 24 часа")
    make_post("post_network.png", "Интернет пропадает?", "Пинг · DNS · Потери пакетов")
    make_post("post_case.png", "SSD: износ 66% — что делать?", "Бэкап · Замена · SMART")
    make_post("post_update.png", "pc-diag 1.1.4 — что нового?", "Обновление · Улучшения")
    make_post("post_month.png", "Топ-3 проблемы месяца", "SSD · Перегрев · Автозагрузка")
    make_post("post_download.png", "Бесплатная диагностика Windows", "60 секунд и понятный отчёт")
    print("OK: cover, avatar, 10 post images")


if __name__ == "__main__":
    main()
