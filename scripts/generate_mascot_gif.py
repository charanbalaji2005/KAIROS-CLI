"""Generate animated GIF for Kairos mascot with eye movement and giggling animations."""

from pathlib import Path
from PIL import Image, ImageDraw


def generate_mascot_gif(output_path: str = "assets/mascot.gif") -> None:
    base_path = Path("assets/mascot.png")
    if not base_path.exists():
        raise FileNotFoundError(f"Base mascot not found at {base_path}")

    base = Image.open(base_path).convert("RGBA")
    bbox = base.getbbox()
    pad = 30
    crop_box = (
        max(0, bbox[0] - pad),
        max(0, bbox[1] - pad),
        min(base.width, bbox[2] + pad),
        min(base.height, bbox[3] + pad),
    )
    robot_cropped = base.crop(crop_box)

    canvas_w = robot_cropped.width + 40
    canvas_h = robot_cropped.height + 40
    ox, oy = crop_box[0], crop_box[1]

    def make_frame(y_offset: int = 0, eye_mode: str = "idle", stars: bool = False) -> Image.Image:
        canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
        r = robot_cropped.copy()
        draw = ImageDraw.Draw(r)

        bg_color = (25, 14, 13, 255)
        glow_color = (254, 160, 68, 255)
        glow_border = (180, 80, 30, 255)

        le_box = (390 - ox, 320 - oy, 416 - ox, 374 - oy)
        re_box = (596 - ox, 320 - oy, 622 - ox, 374 - oy)

        if eye_mode == "blink":
            draw.rectangle(le_box, fill=bg_color)
            draw.rectangle(re_box, fill=bg_color)
            my = (le_box[1] + le_box[3]) // 2
            draw.rectangle((le_box[0], my - 4, le_box[2], my + 4), fill=glow_color, outline=glow_border)
            draw.rectangle((re_box[0], my - 4, re_box[2], my + 4), fill=glow_color, outline=glow_border)
        elif eye_mode == "look_left":
            draw.rectangle(le_box, fill=bg_color)
            draw.rectangle(re_box, fill=bg_color)
            shift = -24
            draw.rectangle((le_box[0] + shift, le_box[1], le_box[2] + shift, le_box[3]), fill=glow_color, outline=glow_border)
            draw.rectangle((re_box[0] + shift, re_box[1], re_box[2] + shift, re_box[3]), fill=glow_color, outline=glow_border)
        elif eye_mode == "look_right":
            draw.rectangle(le_box, fill=bg_color)
            draw.rectangle(re_box, fill=bg_color)
            shift = 24
            draw.rectangle((le_box[0] + shift, le_box[1], le_box[2] + shift, le_box[3]), fill=glow_color, outline=glow_border)
            draw.rectangle((re_box[0] + shift, re_box[1], re_box[2] + shift, re_box[3]), fill=glow_color, outline=glow_border)
        elif eye_mode == "wink":
            draw.rectangle(re_box, fill=bg_color)
            my = (re_box[1] + re_box[3]) // 2
            draw.rectangle((re_box[0], my - 4, re_box[2], my + 4), fill=glow_color, outline=glow_border)
        elif eye_mode == "giggle1":
            draw.rectangle(le_box, fill=bg_color)
            draw.rectangle(re_box, fill=bg_color)
            lx1, ly1, lx2, ly2 = le_box[0], le_box[1], le_box[2], le_box[3]
            draw.line([(lx1, ly1), (lx2, (ly1 + ly2) // 2), (lx1, ly2)], fill=glow_color, width=6)
            rx1, ry1, rx2, ry2 = re_box[0], re_box[1], re_box[2], re_box[3]
            draw.line([(rx2, ry1), (rx1, (ry1 + ry2) // 2), (rx2, ry2)], fill=glow_color, width=6)
        elif eye_mode == "giggle2":
            draw.rectangle(le_box, fill=bg_color)
            draw.rectangle(re_box, fill=bg_color)
            lx1, ly1, lx2, ly2 = le_box[0], le_box[1], le_box[2], le_box[3]
            draw.line([(lx1, ly2), ((lx1 + lx2) // 2, ly1), (lx2, ly2)], fill=glow_color, width=6)
            rx1, ry1, rx2, ry2 = re_box[0], re_box[1], re_box[2], re_box[3]
            draw.line([(rx1, ry2), ((rx1 + rx2) // 2, ry1), (rx2, ry2)], fill=glow_color, width=6)

        canvas.paste(r, (20, 20 - y_offset), r)

        if stars:
            cdraw = ImageDraw.Draw(canvas)
            star_color = (255, 200, 80, 240)
            cx, cy = 20 + 280 - ox, 20 - y_offset + 120 - oy
            cdraw.line([(cx - 8, cy), (cx + 8, cy)], fill=star_color, width=3)
            cdraw.line([(cx, cy - 8), (cx, cy + 8)], fill=star_color, width=3)
            cx2, cy2 = 20 + 740 - ox, 20 - y_offset + 115 - oy
            cdraw.line([(cx2 - 8, cy2), (cx2 + 8, cy2)], fill=star_color, width=3)
            cdraw.line([(cx2, cy2 - 8), (cx2, cy2 + 8)], fill=star_color, width=3)

        return canvas.resize((320, int(320 * canvas_h / canvas_w)), Image.Resampling.LANCZOS)

    sequence = [
        (0, "idle", False, 900),
        (0, "blink", False, 150),
        (0, "idle", False, 300),
        (0, "look_left", False, 450),
        (0, "look_right", False, 450),
        (0, "idle", False, 350),
        (0, "wink", False, 250),
        (0, "idle", False, 250),
        # Giggle bounce sequence
        (6, "giggle1", True, 130),
        (14, "giggle2", True, 150),
        (8, "giggle1", True, 130),
        (14, "giggle2", True, 150),
        (6, "giggle1", True, 130),
        (0, "idle", False, 700),
    ]

    gif_frames = []
    durations = []
    for y_off, mode, st, dur in sequence:
        f = make_frame(y_off, mode, st)
        alpha = f.split()[3]
        f_p = f.convert("RGB").convert("P", palette=Image.ADAPTIVE, colors=255)
        mask = Image.eval(alpha, lambda a: 255 if a <= 128 else 0)
        f_p.paste(255, mask)
        f_p.info["transparency"] = 255
        gif_frames.append(f_p)
        durations.append(dur)

    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    gif_frames[0].save(
        out_file,
        save_all=True,
        append_images=gif_frames[1:],
        duration=durations,
        loop=0,
        disposal=2,
        optimize=False,
    )
    print(f"Mascot animated GIF generated at {out_file}")


if __name__ == "__main__":
    generate_mascot_gif()
