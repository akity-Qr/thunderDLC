from PIL import Image, ImageDraw

def create_ico():
    size = 256
    scale = 4
    big = size * scale
    img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 1. Тёмный фон с закруглёнными углами
    radius = int(big * 0.22)
    draw.rounded_rectangle([0, 0, big - 1, big - 1], radius=radius, fill=(18, 18, 18, 255))

    # 2. Светлый ромб
    c = big / 2
    r = big * 0.30
    diamond = [(c, c - r), (c + r, c), (c, c + r), (c - r, c)]
    draw.line(diamond + [diamond[0]], fill=(230, 230, 230, 255), width=int(4 * scale), joint="curve")

    # 3. Белая молния в центре
    bolt = [
        (c + big * 0.045, c - big * 0.16),
        (c - big * 0.09, c + big * 0.02),
        (c - big * 0.008, c + big * 0.02),
        (c - big * 0.06, c + big * 0.17),
        (c + big * 0.11, c - big * 0.02),
        (c + big * 0.015, c - big * 0.02),
    ]
    draw.polygon(bolt, fill=(255, 255, 255, 255))

    # 4. Сохранение в .ico со всеми размерами для Windows
    base_img = img.resize((size, size), Image.LANCZOS)
    base_img.save("icon.ico", format="ICO", sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
    print("Готово! Файл icon.ico появился в папке.")

if __name__ == "__main__":
    create_ico()