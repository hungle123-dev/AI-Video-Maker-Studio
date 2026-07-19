"""TubeCraft tech-dark scene pack #5."""
import json

from core.custom_scenes import scene
from core.scene_bodies import BODIES


ACCENT = {
    "cyan": "#22d3ee",
    "green": "#34d399",
    "orange": "#fb923c",
    "yellow": "#fbbf24",
    "red": "#f87171",
    "purple": "#a78bfa",
    "blue": "#38bdf8",
}
TXT = "#f5f7f9"
_JS_AC = "var AC=" + json.dumps(ACCENT, ensure_ascii=False) + ";"


def _hex_rgba(hex_color, alpha):
    value = str(hex_color or "").lstrip("#")
    if len(value) != 6:
        return f"rgba(34,211,238,{alpha})"
    return f"rgba({int(value[:2], 16)},{int(value[2:4], 16)},{int(value[4:], 16)},{alpha})"


def _ac(name, fallback="cyan"):
    return ACCENT.get(name, ACCENT[fallback])


def td_chat_rail(
    left_title="Chat thường: một lượt",
    bubbles=None,
    left_end="Kết thúc",
    right_title="Việc phức tạp: trạng thái tiến dần",
    stations=None,
    right_note="cùng một trạng thái, đi từng trạm",
):
    bubbles = [str(value) for value in (bubbles or ["Hỏi một câu", "Đáp một câu"])][:2]
    while len(bubbles) < 2:
        bubbles.append("")
    stations = stations or [
        {"icon": "📄", "label": "Đọc tin", "color": "cyan"},
        {"icon": "⚙️", "label": "Gọi tool", "color": "yellow"},
        {"icon": "📥", "label": "Lấy kết quả", "color": "green"},
        {"icon": "🎯", "label": "Đánh giá lại", "color": "purple"},
    ]
    colors = ("cyan", "yellow", "green", "purple")
    normalized = []
    for index, item in enumerate(stations[:4]):
        if not isinstance(item, dict):
            item = {"label": str(item)}
        normalized.append(
            {
                "icon": str(item.get("icon", "•")),
                "label": str(item.get("label", "")),
                "c": str(item.get("color", colors[index % len(colors)])),
            }
        )
    return scene(
        [
            _JS_AC,
            "var LT=" + json.dumps(str(left_title), ensure_ascii=False) + ";",
            "var BB=" + json.dumps(bubbles, ensure_ascii=False) + ";",
            "var LE=" + json.dumps(str(left_end), ensure_ascii=False) + ";",
            "var RT=" + json.dumps(str(right_title), ensure_ascii=False) + ";",
            "var ST=" + json.dumps(normalized, ensure_ascii=False) + ";",
            "var RN=" + json.dumps(str(right_note), ensure_ascii=False) + ";",
            BODIES["td_chat_rail"],
        ],
        560,
    )


def td_title_hero(
    kicker="— GIẢI PHẪU CƠ CHẾ",
    lines=None,
    sub="Không phải chat dài hơn — mà là tiến từng vòng quanh trạng thái.",
    ring=None,
    center="Vòng tác vụ",
    color="cyan",
):
    lines = lines or [
        {"text": "Claude chạy", "color": "white"},
        {"text": "vòng lặp tác vụ", "color": "yellow"},
        {"text": "như thế nào", "color": "green"},
    ]
    normalized = []
    for item in lines[:3]:
        if not isinstance(item, dict):
            item = {"text": str(item)}
        color_name = str(item.get("color", "white"))
        normalized.append(
            {
                "t": str(item.get("text", "")),
                "c": TXT if color_name == "white" else _ac(color_name),
            }
        )
    ring = [str(value) for value in (ring or ["Nhận", "Đánh giá", "Tool", "Lặp", "Xong"])][:5]
    node_colors = ["cyan", "blue", "yellow", "orange", "green"][: len(ring)]
    return scene(
        [
            _JS_AC,
            "var KK=" + json.dumps(str(kicker).lstrip("— "), ensure_ascii=False) + ";",
            "var LN=" + json.dumps(normalized, ensure_ascii=False) + ";",
            "var SB=" + json.dumps(str(sub), ensure_ascii=False) + ";",
            "var RG=" + json.dumps(ring, ensure_ascii=False) + ";",
            "var CT=" + json.dumps(str(center), ensure_ascii=False) + ";",
            "var NC=" + json.dumps(node_colors) + ";",
            "var ACC=" + json.dumps(_ac(str(color))) + ";",
            BODIES["td_title_hero"],
        ],
        560,
    )


def td_outro(
    name="Kênh của bạn",
    done="Hết tập này",
    ask_tag="Tập sau mổ gì",
    ask="Chủ đề A, hay chủ đề B?",
    follow="Theo dõi — tập sau nói kỹ",
    save="Lưu lại — xem lại ý chính",
    quote="Hiểu vòng lặp trước, rồi hãy điều khiển nó.",
    tags=None,
):
    def _split(value):
        value = str(value)
        if "—" in value:
            head, tail = value.split("—", 1)
            return head.strip(), tail.strip()
        parts = value.split(" ", 2)
        return (
            (" ".join(parts[:2]), parts[2])
            if len(parts) >= 3
            else (value, "")
        )

    follow_head, follow_tail = _split(follow)
    save_head, save_tail = _split(save)
    tags = [str(value) for value in (tags or ["#AI", "#LLM", "#Claude"])][:6]
    return scene(
        [
            _JS_AC,
            "var NM=" + json.dumps(str(name), ensure_ascii=False) + ";",
            "var DN=" + json.dumps(str(done), ensure_ascii=False) + ";",
            "var AT=" + json.dumps(str(ask_tag), ensure_ascii=False) + ";",
            "var AS=" + json.dumps(str(ask), ensure_ascii=False) + ";",
            "var FH="
            + json.dumps(follow_head, ensure_ascii=False)
            + ", FT="
            + json.dumps(follow_tail, ensure_ascii=False)
            + ";",
            "var SH="
            + json.dumps(save_head, ensure_ascii=False)
            + ", ST2="
            + json.dumps(save_tail, ensure_ascii=False)
            + ";",
            "var QT=" + json.dumps(str(quote), ensure_ascii=False) + ";",
            "var TG=" + json.dumps(tags, ensure_ascii=False) + ";",
            BODIES["td_outro"],
        ],
        640,
    )


SCENES = {
    "td_chat_rail": {
        "fn": td_chat_rail,
        "doc": 'td_chat_rail {"left_title":"Chat thường: một lượt","bubbles":["Hỏi","Đáp"],"left_end":"Kết thúc","right_title":"Việc phức tạp: trạng thái tiến dần","stations":[{"icon":"📄","label":"Đọc tin"}],"right_note":"..."} — so sánh chat 1 lượt (2 bong bóng, kết thúc) với đường ray tác vụ chéo lên 4 trạm icon',
        "demo": {
            "left_title": "Chat thường: một lượt",
            "bubbles": ["Hỏi một câu", "Đáp một câu"],
            "left_end": "Kết thúc",
            "right_title": "Việc phức tạp: trạng thái tiến dần",
            "stations": [
                {"icon": "📄", "label": "Đọc tin"},
                {"icon": "⚙️", "label": "Gọi tool"},
                {"icon": "📥", "label": "Lấy kết quả"},
                {"icon": "🎯", "label": "Đánh giá lại"},
            ],
            "right_note": "cùng một trạng thái, đi từng trạm",
        },
    },
    "td_title_hero": {
        "fn": td_title_hero,
        "doc": 'td_title_hero {"kicker":"— GIẢI PHẪU CƠ CHẾ","lines":[{"text":"...","color":"white|yellow|green|cyan|orange"}],"sub":"...","ring":["Nhận","Đánh giá","Tool","Lặp","Xong"],"center":"Vòng tác vụ","color":"cyan"} — mở bài: headline 3 dòng nhiều màu + card vòng tròn 5 node bước sáng lần lượt',
        "demo": {
            "kicker": "— GIẢI PHẪU CƠ CHẾ",
            "lines": [
                {"text": "Claude chạy", "color": "white"},
                {"text": "vòng lặp tác vụ", "color": "yellow"},
                {"text": "như thế nào", "color": "green"},
            ],
            "sub": "Không phải chat dài hơn — mà là tiến từng vòng quanh trạng thái.",
            "ring": ["Nhận", "Đánh giá", "Tool", "Lặp", "Xong"],
            "center": "Vòng tác vụ",
            "color": "cyan",
        },
    },
    "td_outro": {
        "fn": td_outro,
        "doc": 'td_outro {"name":"Kênh của bạn","done":"Hết tập này","ask_tag":"Tập sau mổ gì","ask":"Chủ đề A, hay chủ đề B?","follow":"Theo dõi — tập sau nói kỹ","save":"Lưu lại — xem lại ý chính","quote":"...","tags":["#AI"]} — kết video: avatar vòng gradient quay + card hỏi tập sau + 2 CTA + quote vàng + hashtag',
        "demo": {
            "name": "Kênh của bạn",
            "done": "Hết tập này",
            "ask_tag": "Tập sau mổ gì",
            "ask": "Chủ đề A, hay chủ đề B?",
            "follow": "Theo dõi — tập sau nói kỹ",
            "save": "Lưu lại — xem lại ý chính",
            "quote": "Hiểu vòng lặp trước, rồi hãy điều khiển nó.",
            "tags": ["#AI", "#LLM", "#Claude"],
        },
    },
}
