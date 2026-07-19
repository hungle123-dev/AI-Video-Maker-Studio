"""TubeCraft warm-paper scene pack #1."""
import json

from core.custom_scenes import scene
from core.scene_bodies import BODIES


INK = "#211a12"
ACCENT = {
    "orange": "#e8590c",
    "red": "#d9480f",
    "blue": "#1c7ed6",
    "green": "#2f9e44",
    "gray": "#adb5bd",
}


def _hex_rgba(hex_color, alpha):
    h = hex_color.lstrip("#")
    return "rgba(%d,%d,%d,%s)" % (
        int(h[0:2], 16),
        int(h[2:4], 16),
        int(h[4:6], 16),
        alpha,
    )


def _ac(name, fallback="orange"):
    return ACCENT.get(name, ACCENT[fallback])


def wp_chrome(brand="Tên Kênh", color="orange"):
    el = scene(
        [
            "var BR=" + json.dumps(str(brand), ensure_ascii=False) + ";",
            BODIES["wp_chrome"],
        ],
        1800,
    )
    el.update(x_9_16=0.0, y_9_16=0.03125, x_16_9=0.0, y_16_9=0.03125)
    return el


def wp_title_stack(tag="KẾT LUẬN", color="blue", lines=None, subs=None):
    ac = _ac(str(color), "blue")
    lines = lines or [
        {"text": "Một nhà đóng cửa", "color": "ink"},
        {"text": "Một nhà mở nguồn", "color": "orange"},
    ]
    norm = []
    for item in lines[:4]:
        if not isinstance(item, dict):
            item = {"text": str(item)}
        cname = str(item.get("color", "ink"))
        norm.append(
            {
                "t": str(item.get("text", "")),
                "c": INK if cname == "ink" else _ac(cname),
            }
        )
    subs = [str(value) for value in (subs or [])][:2]
    count = max(1, len(norm))
    sy0 = 162 + count * 108
    height = 130 + count * 108 + (82 if subs else 0) + (
        52 if len(subs) > 1 else 0
    )
    return scene(
        [
            "var TAG=" + json.dumps(str(tag), ensure_ascii=False) + ";",
            "var LS=" + json.dumps(norm, ensure_ascii=False) + ";",
            "var SB=" + json.dumps(subs, ensure_ascii=False) + ";",
            "var ACC=" + json.dumps(ac) + ";",
            "var ACB=" + json.dumps(_hex_rgba(ac, 0.45)) + ";",
            "var ACF=" + json.dumps(_hex_rgba(ac, 0.12)) + ";",
            "var SY0=" + str(sy0) + ";",
            BODIES["wp_title_stack"],
        ],
        height,
    )


def wp_outro(
    brand="Tên Kênh",
    tagline="Theo dõi để nắm AI mỗi tuần",
    actions=None,
    platforms=None,
):
    actions = actions or [
        {"icon": "👍", "label": "Thích", "color": "orange"},
        {"icon": "💰", "label": "Ủng hộ", "color": "orange"},
        {"icon": "⭐", "label": "Lưu lại", "color": "orange"},
        {"icon": "✓", "label": "Đã theo dõi", "color": "green"},
    ]
    norm = []
    for item in actions[:4]:
        if not isinstance(item, dict):
            item = {"label": str(item)}
        cname = str(item.get("color", "orange"))
        norm.append(
            {
                "i": str(item.get("icon", "")),
                "l": str(item.get("label", "")),
                "c": _ac(cname),
                "g": 1 if cname == "green" else 0,
            }
        )
    platforms = [str(value) for value in (platforms or ["🎵", "📺", "▶"])][:5]
    return scene(
        [
            "var BR=" + json.dumps(str(brand), ensure_ascii=False) + ";",
            "var TL=" + json.dumps(str(tagline), ensure_ascii=False) + ";",
            "var AS=" + json.dumps(norm, ensure_ascii=False) + ";",
            "var PL=" + json.dumps(platforms, ensure_ascii=False) + ";",
            BODIES["wp_outro"],
        ],
        640,
    )


SCENES = {
    "wp_chrome": {
        "fn": wp_chrome,
        "doc": 'wp_chrome {"brand":"Tên Kênh","color":"orange"} — khung kênh nền kem: brand xám góc trên-phải + vạch gradient đỏ→cam→xanh full-width ở đáy (element ĐẦU TIÊN của mọi step)',
        "demo": {"brand": "MỔ XẺ CÔNG NGHỆ", "color": "orange"},
    },
    "wp_title_stack": {
        "fn": wp_title_stack,
        "doc": 'wp_title_stack {"tag":"KẾT LUẬN","color":"blue","lines":[{"text":"Một nhà đóng cửa","color":"ink"},{"text":"Một nhà mở nguồn","color":"orange"}],"subs":["dòng phụ"]} — mở bài/kết luận typographic: chip tag + 2-4 dòng chữ rất lớn màu ink/accent reveal lần lượt + tối đa 2 dòng phụ xám',
        "demo": {
            "tag": "KẾT LUẬN",
            "color": "blue",
            "lines": [
                {"text": "Một nhà đóng cửa", "color": "ink"},
                {"text": "Một nhà mở nguồn", "color": "orange"},
                {"text": "Một nhà làm Apple", "color": "ink"},
                {"text": "Một nhà làm Android", "color": "blue"},
            ],
            "subs": [
                "Không ai đúng ai sai — chỉ là hai triết lý",
                "Người dùng cuối là bên thắng",
            ],
        },
    },
    "wp_outro": {
        "fn": wp_outro,
        "doc": 'wp_outro {"brand":"Tên Kênh","tagline":"...","actions":[{"icon":"👍","label":"Thích","color":"orange"}],"platforms":["🎵","📺","▶"]} — kết video: brand lớn + tagline + 4 nút card trắng (nút green nền xanh nhạt) + hàng platform icon mờ',
        "demo": {
            "brand": "MỔ XẺ CÔNG NGHỆ",
            "tagline": "Theo dõi để nắm AI mỗi tuần",
            "actions": [
                {"icon": "👍", "label": "Thích", "color": "orange"},
                {"icon": "💰", "label": "Ủng hộ", "color": "orange"},
                {"icon": "⭐", "label": "Lưu lại", "color": "orange"},
                {"icon": "✓", "label": "Đã theo dõi", "color": "green"},
            ],
            "platforms": ["🎵", "📺", "▶"],
        },
    },
}
