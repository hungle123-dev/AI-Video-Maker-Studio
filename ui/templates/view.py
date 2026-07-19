"""Trang quản lý và chỉnh sửa toàn bộ template local."""

import threading

import flet as ft

from ui.theme import COLORS


STYLE_VI = {
    "liquidglass": "Liquid Glass",
    "cyberpunk": "Cyberpunk",
    "watercolor": "Màu nước",
    "aurora": "Aurora (sáng)",
    "cartoon": "Cartoon",
    "sketchnote": "Sketchnote",
    "pastel": "Pastel",
    "inkwash": "Mực tàu",
    "pixel": "Pixel 8-bit",
    "default": "Gradient tối",
    "sketch": "Sketch",
}
EFFECT_VI = {
    "counter_metric": "Số liệu tăng",
    "bar_compare": "So sánh cột",
    "growth_curve": "Đường cong",
    "orbit_ecosystem": "Quỹ đạo",
    "step_reveal_list": "Checklist",
    "gauge_dial": "Đồng hồ đo",
    "flow_pipeline": "Pipeline",
    "leak_bucket": "Rò rỉ",
    "flat_stat": "Số phẳng",
    "donut_percent": "Vòng tròn %",
    "star_rating": "Sao đánh giá",
    "timeline_road": "Dòng thời gian",
    "quote_card": "Trích dẫn",
    "icon_grid": "Lưới icon",
}
class TemplatesView(ft.Column):
    def __init__(self, page: ft.Page):
        super().__init__(
            spacing=16,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            alignment=ft.MainAxisAlignment.START,
        )
        self.page = page
        self._imgs = {}
        self._spins = {}
        self._pngs = {}
        self._aspect = "9:16"
        self._build()
        threading.Thread(target=self._ensure_all, daemon=True).start()

    def _dims(self):
        base_w = {"16:9": 300, "1:1": 214}.get(self._aspect, 196)
        width_ratio, height_ratio = (int(x) for x in self._aspect.split(":"))
        image_height = int(base_w * height_ratio / width_ratio)
        return base_w, image_height, base_w + 18, image_height + 206

    def _build(self):
        from core.templates import list_templates

        self.img_w, self.img_h, self.card_w, self.card_h = self._dims()
        self.status = ft.Text("", size=12, color=COLORS["text_secondary"])
        self.refresh_btn = ft.OutlinedButton(
            "Render lại tất cả",
            icon=ft.Icons.REFRESH_ROUNDED,
            on_click=self._rerender_all,
        )
        self.fontstore_btn = ft.FilledButton(
            "Kho font online",
            icon=ft.Icons.CLOUD_DOWNLOAD_ROUNDED,
            on_click=self._font_store_dialog,
        )
        size_chips = ft.Row(
            [
                ft.Text("Kích thước:", size=12, color=COLORS["text_secondary"]),
                self._aspect_chip(
                    "9:16", "9:16 Dọc", ft.Icons.STAY_CURRENT_PORTRAIT_ROUNDED
                ),
                self._aspect_chip(
                    "16:9", "16:9 Ngang", ft.Icons.STAY_CURRENT_LANDSCAPE_ROUNDED
                ),
                self._aspect_chip("1:1", "1:1 Vuông", ft.Icons.CROP_SQUARE_ROUNDED),
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        cards = [self._card(template) for template in list_templates()]

        self.controls = [
            ft.Row(
                [
                    ft.Column(
                        [
                            ft.Text(
                                "Template mẫu",
                                size=24,
                                weight=ft.FontWeight.BOLD,
                                color=COLORS["text"],
                            ),
                            ft.Text(
                                "Combo nền · màu · font · hiệu ứng. Bấm ✎ để sửa; "
                                "ảnh là frame render thật từ engine.",
                                size=13,
                                color=COLORS["text_secondary"],
                            ),
                        ],
                        spacing=2,
                        expand=True,
                    ),
                    ft.Column(
                        [
                            ft.Row(
                                [
                                    self.fontstore_btn,
                                    self.refresh_btn,
                                ],
                                spacing=8,
                            ),
                            self.status,
                        ],
                        spacing=6,
                        horizontal_alignment=ft.CrossAxisAlignment.END,
                    ),
                ],
                vertical_alignment=ft.CrossAxisAlignment.START,
            ),
            size_chips,
            ft.Row(cards, wrap=True, spacing=18, run_spacing=20),
        ]

    def _aspect_chip(self, aspect, label, icon):
        selected = self._aspect == aspect
        return ft.Container(
            on_click=lambda _, value=aspect: self._set_aspect(value),
            ink=True,
            bgcolor=COLORS["accent"] if selected else COLORS["bg_card"],
            border=ft.border.all(
                1, COLORS["accent"] if selected else COLORS["border"]
            ),
            border_radius=20,
            padding=ft.padding.symmetric(horizontal=12, vertical=6),
            content=ft.Row(
                [
                    ft.Icon(
                        icon,
                        size=15,
                        color="white" if selected else COLORS["text_secondary"],
                    ),
                    ft.Text(
                        label,
                        size=12,
                        weight=ft.FontWeight.BOLD,
                        color="white" if selected else COLORS["text"],
                    ),
                ],
                spacing=6,
                tight=True,
            ),
        )

    def _set_aspect(self, aspect):
        if aspect == self._aspect:
            return
        self._aspect = aspect
        self._reload()
        threading.Thread(target=self._ensure_all, daemon=True).start()

    def _hover_preview(self, e, tid, gif):
        if not gif:
            return
        image = self._imgs.get(tid)
        if image is None:
            return
        source = gif if str(e.data).lower() == "true" else self._pngs.get(tid)
        if not source or image.src == source:
            return
        image.src = source
        try:
            image.update()
        except Exception:
            try:
                self.page.update()
            except Exception:
                pass

    @staticmethod
    def _play_hint(**pos):
        return ft.Container(
            **pos,
            bgcolor="#0e1420cc",
            border_radius=20,
            padding=ft.padding.symmetric(horizontal=7, vertical=2),
            tooltip="Rê chuột để xem preview động",
            content=ft.Text("▶", size=10, weight=ft.FontWeight.BOLD, color="white"),
        )

    def _card(self, t):
        template = t
        from core.templates import has_thumb, is_customized, thumb_path

        tid = template["id"]
        exists = has_thumb(tid, self._aspect)
        png = str(thumb_path(tid, self._aspect)) if exists else None
        image = ft.Image(
            src=png,
            width=self.img_w,
            height=self.img_h,
            fit=ft.ImageFit.COVER,
            border_radius=12,
            gapless_playback=True,
        )
        self._imgs[tid] = image
        self._pngs[tid] = png
        gif = str(template.get("gif") or "")
        spinner = ft.Container(
            width=self.img_w,
            height=self.img_h,
            border_radius=12,
            bgcolor="#0e142088",
            alignment=ft.alignment.center,
            visible=not exists,
            content=ft.Column(
                [
                    ft.ProgressRing(
                        width=26,
                        height=26,
                        stroke_width=3,
                        color=COLORS["accent"],
                    ),
                    ft.Text("Đang render…", size=11, color="white"),
                ],
                spacing=8,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
        )
        self._spins[tid] = spinner
        overlays = [
            ft.Container(
                width=self.img_w,
                height=self.img_h,
                border_radius=12,
                bgcolor="#0e1420",
                content=image,
            ),
            spinner,
            ft.Container(
                left=8,
                top=8,
                content=ft.IconButton(
                    ft.Icons.EDIT_ROUNDED,
                    icon_size=15,
                    icon_color="white",
                    bgcolor="#0e1420cc",
                    tooltip="Sửa template",
                    on_click=lambda _, key=tid: self._edit_dialog(key),
                    style=ft.ButtonStyle(
                        padding=6, shape=ft.RoundedRectangleBorder(radius=9)
                    ),
                ),
            ),
        ]
        if tid == "lux_finance":
            overlays.append(
                ft.Container(
                    right=8,
                    top=8,
                    bgcolor=COLORS["yellow"],
                    border_radius=20,
                    padding=ft.padding.symmetric(horizontal=8, vertical=2),
                    content=ft.Text(
                        "Đề xuất", size=10, weight=ft.FontWeight.BOLD, color="white"
                    ),
                )
            )
        if is_customized(tid):
            overlays.append(
                ft.Container(
                    right=8,
                    bottom=8,
                    bgcolor=COLORS["accent"],
                    border_radius=20,
                    padding=ft.padding.symmetric(horizontal=8, vertical=2),
                    content=ft.Text(
                        "Đã chỉnh", size=10, weight=ft.FontWeight.BOLD, color="white"
                    ),
                )
            )
        if gif:
            overlays.append(self._play_hint(left=8, bottom=8))

        frame = ft.Container(
            padding=8,
            border_radius=18,
            bgcolor="#0e1420",
            border=ft.border.all(1, "#ffffff1a"),
            on_hover=(lambda e: self._hover_preview(e, tid, gif)) if gif else None,
            content=ft.Stack(overlays, width=self.img_w, height=self.img_h),
        )
        style = STYLE_VI.get(template["art_style"], template["art_style"])
        font = template["font_family"] or "Phong cách"
        title_color = template["title_color"]
        return ft.Container(
            width=self.card_w,
            height=self.card_h,
            alignment=ft.alignment.top_left,
            content=ft.Column(
                [
                    frame,
                    ft.Row(
                        [
                            ft.Text(template["emoji"], size=17),
                            ft.Text(
                                template["name"],
                                size=15,
                                weight=ft.FontWeight.BOLD,
                                color=COLORS["text"],
                                expand=True,
                            ),
                        ],
                        spacing=6,
                    ),
                    ft.Text(
                        template["desc"],
                        size=12,
                        color=COLORS["text_secondary"],
                        max_lines=2,
                    ),
                    ft.Row(
                        [self._chip("Style", style), self._chip("Font", font)],
                        spacing=6,
                        wrap=True,
                    ),
                    ft.Row(
                        [
                            self._chip(
                                "Màu",
                                title_color.upper() if title_color else "Theo style",
                                swatch=title_color or None,
                            ),
                            self._chip(
                                "Hiệu ứng",
                                EFFECT_VI.get(
                                    template.get("effect"), template.get("effect", "—")
                                ),
                            ),
                        ],
                        spacing=6,
                        wrap=True,
                    ),
                ],
                spacing=9,
            ),
        )

    def _chip(self, k, v, swatch=None):
        key, value = k, v
        row = [
            ft.Text(
                key.upper(),
                size=9,
                color=COLORS["text_secondary"],
                weight=ft.FontWeight.BOLD,
            )
        ]
        if swatch:
            row.append(
                ft.Container(
                    width=11,
                    height=11,
                    border_radius=3,
                    bgcolor=swatch,
                    border=ft.border.all(1, COLORS["border"]),
                )
            )
        row.append(
            ft.Text(str(value), size=11, color=COLORS["text"], font_family="Consolas")
        )
        return ft.Container(
            bgcolor=COLORS["bg_glass"],
            border_radius=7,
            padding=ft.padding.symmetric(horizontal=8, vertical=3),
            border=ft.border.all(1, COLORS["border"]),
            content=ft.Row(row, spacing=5, tight=True),
        )

    def _edit_dialog(self, tid):
        from core.fonts import font_options
        from core.templates import (
            EFFECT_OPTIONS,
            STYLE_OPTIONS,
            TITLE_COLOR_OPTIONS,
            get_template,
            is_customized,
            reset_template,
            update_template,
        )

        template = get_template(tid)
        name = ft.TextField(label="Tên template", value=template["name"], filled=True)
        topic = ft.TextField(
            label="Chủ đề ảnh mẫu",
            value=template.get("topic", ""),
            filled=True,
            hint_text="Tiêu đề hiển thị trên thumbnail",
        )
        art_style = ft.Dropdown(
            label="Phong cách / nền",
            value=template["art_style"],
            filled=True,
            options=[ft.dropdown.Option(value, label) for value, label in STYLE_OPTIONS],
        )
        title_color = ft.Dropdown(
            label="Màu tiêu đề",
            value=template["title_color"],
            filled=True,
            options=[
                ft.dropdown.Option(value, label) for value, label in TITLE_COLOR_OPTIONS
            ],
        )
        font_family = ft.Dropdown(
            label="Font chữ",
            value=template["font_family"],
            filled=True,
            options=[ft.dropdown.Option(value, label) for value, label in font_options()],
        )
        font_note = ft.Text("", size=11, color=COLORS["text_secondary"])

        def _check_font(_=None):
            from core.fonts import is_vietnamese

            family = font_family.value or ""
            if family and not is_vietnamese(family):
                font_note.value = (
                    "⚠ Font này thiếu dấu tiếng Việt — nên chọn font có ✓ Tiếng Việt."
                )
                font_note.color = COLORS["orange"]
            elif not family:
                font_note.value = "Dùng font mặc định của phong cách."
                font_note.color = COLORS["text_secondary"]
            else:
                font_note.value = "✓ Font hỗ trợ đầy đủ dấu tiếng Việt."
                font_note.color = COLORS["green"]
            self.page.update()

        font_family.on_change = _check_font

        def on_pick(event):
            if not event.files:
                return
            try:
                from core.fonts import add_font, font_options as all_fonts

                record = add_font(event.files[0].path)
                font_family.options = [
                    ft.dropdown.Option(value, label) for value, label in all_fonts()
                ]
                font_family.value = record["family"]
                _check_font()
                vietnamese = "✓ hỗ trợ" if record.get("vietnamese") else "⚠ THIẾU"
                self.page.open(
                    ft.SnackBar(
                        ft.Text(
                            f"Đã thêm font '{record['display']}' — {vietnamese} dấu tiếng Việt."
                        )
                    )
                )
                self.page.update()
            except Exception as ex:
                self.page.open(ft.SnackBar(ft.Text(f"Lỗi thêm font: {ex}")))

        if getattr(self, "_picker", None) is None:
            self._picker = ft.FilePicker()
            self.page.overlay.append(self._picker)
            self.page.update()
        self._picker.on_result = on_pick
        add_font_btn = ft.IconButton(
            ft.Icons.ADD_ROUNDED,
            tooltip="Thêm font .ttf / .otf",
            on_click=lambda _: self._picker.pick_files(
                allow_multiple=False,
                allowed_extensions=["ttf", "otf"],
                dialog_title="Chọn file font (.ttf/.otf)",
            ),
        )
        effect = ft.Dropdown(
            label="Hiệu ứng ảnh mẫu",
            value=template.get("effect", "counter_metric"),
            filled=True,
            options=[ft.dropdown.Option(value, label) for value, label in EFFECT_OPTIONS],
        )

        def save(_):
            from core.templates import clear_thumbs

            update_template(
                tid,
                name=name.value.strip() or template["name"],
                topic=topic.value.strip(),
                art_style=art_style.value,
                title_color=title_color.value,
                font_family=font_family.value,
                effect=effect.value,
            )
            clear_thumbs(tid)
            self.page.close(dlg)
            self._reload()
            self._rerender_one(tid)

        def reset(_):
            from core.templates import clear_thumbs

            reset_template(tid)
            clear_thumbs(tid)
            self.page.close(dlg)
            self._reload()
            self._rerender_one(tid)

        actions = [ft.TextButton("Huỷ", on_click=lambda _: self.page.close(dlg))]
        if is_customized(tid):
            actions.append(
                ft.TextButton(
                    "Khôi phục gốc", icon=ft.Icons.RESTORE_ROUNDED, on_click=reset
                )
            )
        actions.append(
            ft.FilledButton(
                "Lưu & render lại", icon=ft.Icons.SAVE_ROUNDED, on_click=save
            )
        )
        dlg = ft.AlertDialog(
            title=ft.Row(
                [
                    ft.Icon(ft.Icons.EDIT_ROUNDED, color=COLORS["accent"]),
                    ft.Text(
                        f"Sửa · {template['emoji']} {template['name']}",
                        weight=ft.FontWeight.BOLD,
                    ),
                ],
                spacing=10,
            ),
            content=ft.Container(
                width=460,
                content=ft.Column(
                    [
                        name,
                        topic,
                        art_style,
                        title_color,
                        ft.Row(
                            [font_family, add_font_btn],
                            spacing=4,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        font_note,
                        effect,
                        ft.Text(
                            "Đổi phong cách sẽ đổi cả nền & bảng màu. Lưu xong ảnh mẫu tự render lại.",
                            size=11,
                            color=COLORS["text_secondary"],
                        ),
                    ],
                    spacing=12,
                    tight=True,
                    scroll=ft.ScrollMode.AUTO,
                ),
            ),
            actions=actions,
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.open(dlg)
        _check_font()

    def _font_store_dialog(self, e):
        from core.font_store import REGIONS

        region = ft.Dropdown(
            label="Quốc gia / ngôn ngữ",
            value="vietnamese",
            filled=True,
            expand=True,
            options=[ft.dropdown.Option(value, label) for value, label in REGIONS],
        )
        search = ft.TextField(
            label="Tìm tên font",
            filled=True,
            expand=True,
            prefix_icon=ft.Icons.SEARCH_ROUNDED,
            on_submit=lambda _: do_search(),
        )
        info = ft.Text("", size=12, color=COLORS["text_secondary"])
        result_list = ft.Column(
            [], spacing=6, scroll=ft.ScrollMode.AUTO, expand=True
        )
        previews = []
        sample = "Việt Nam · Ngày mới 0123"
        loading = ft.Row(
            [
                ft.ProgressRing(width=18, height=18, stroke_width=2),
                ft.Text("Đang tải danh sách…", size=12, color=COLORS["text_secondary"]),
            ],
            spacing=8,
            visible=False,
        )

        def installed_set():
            from core.fonts import list_fonts

            return {font["family"] for font in list_fonts() if font["user"]}

        def row(font):
            family = font["family"]
            installed = family in installed_set()
            badge = (
                ft.Container(
                    bgcolor=COLORS["green"] + "22",
                    border_radius=6,
                    padding=ft.padding.symmetric(horizontal=6, vertical=1),
                    content=ft.Text("✓ dấu", size=10, color=COLORS["green"]),
                )
                if font.get("vietnamese")
                else ft.Container()
            )
            button = ft.FilledButton(
                "Đã cài" if installed else "Cài",
                icon=ft.Icons.DOWNLOAD_ROUNDED,
                disabled=installed,
                height=34,
            )

            def install(_):
                button.text = "Đang cài…"
                button.disabled = True
                self.page.update()

                def work():
                    try:
                        from core.font_store import install_font

                        record = install_font(family, subset=region.value)
                        button.text = "Đã cài"
                        button.icon = ft.Icons.CHECK_ROUNDED
                        vietnamese = (
                            "✓ đủ dấu TV"
                            if record.get("vietnamese")
                            else "⚠ thiếu dấu TV"
                        )
                        self.page.open(
                            ft.SnackBar(
                                ft.Text(
                                    f"Đã cài '{family}' — {vietnamese}. Chọn được trong ô Font."
                                )
                            )
                        )
                    except Exception as ex:
                        button.text = "Lỗi — thử lại"
                        button.disabled = False
                        self.page.open(ft.SnackBar(ft.Text(f"Lỗi tải font: {ex}")))
                    self.page.update()

                threading.Thread(target=work, daemon=True).start()

            button.on_click = install
            holder = ft.Container(
                height=32,
                alignment=ft.alignment.center_left,
                content=ft.Text(
                    "đang tải chữ mẫu…",
                    size=11,
                    italic=True,
                    color=COLORS["text_secondary"],
                ),
            )
            previews.append((family, holder))
            return ft.Container(
                bgcolor=COLORS["bg_glass"],
                border_radius=10,
                padding=12,
                border=ft.border.all(1, COLORS["border"]),
                content=ft.Row(
                    [
                        ft.Column(
                            [
                                ft.Row(
                                    [
                                        ft.Text(
                                            family,
                                            size=13,
                                            weight=ft.FontWeight.BOLD,
                                            color=COLORS["text"],
                                        ),
                                        ft.Text(
                                            font["category"],
                                            size=10,
                                            color=COLORS["text_secondary"],
                                        ),
                                        badge,
                                    ],
                                    spacing=8,
                                ),
                                holder,
                            ],
                            spacing=5,
                            expand=True,
                        ),
                        button,
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            )

        def _load_previews():
            from concurrent.futures import ThreadPoolExecutor, as_completed

            from core.font_store import render_sample

            pairs = list(previews)
            subset = region.value

            def work(item):
                family, holder = item
                try:
                    return holder, render_sample(family, subset, sample)
                except Exception:
                    return holder, None

            with ThreadPoolExecutor(max_workers=8) as executor:
                futures = [executor.submit(work, item) for item in pairs]
                for done, future in enumerate(as_completed(futures), 1):
                    holder, path = future.result()
                    holder.content = (
                        ft.Image(
                            src=path,
                            height=30,
                            fit=ft.ImageFit.FIT_HEIGHT,
                            gapless_playback=True,
                        )
                        if path
                        else ft.Text(
                            "(không tải được mẫu)",
                            size=11,
                            color=COLORS["text_secondary"],
                        )
                    )
                    if done % 4 == 0:
                        self.page.update()
            self.page.update()

        def do_search():
            loading.visible = True
            result_list.controls = []
            previews.clear()
            info.value = ""
            self.page.update()

            def work():
                try:
                    from core.font_store import list_online, region_count

                    items = list_online(region.value, search.value or "", limit=30)
                    total = region_count(region.value)
                    result_list.controls = [row(font) for font in items]
                    info.value = (
                        f"{total} font — hiện {len(items)}. Đang tải chữ mẫu… "
                        "Gõ tên để tìm thêm."
                    )
                    loading.visible = False
                    self.page.update()
                    _load_previews()
                    info.value = f"{total} font hỗ trợ — hiện {len(items)} kết quả."
                except Exception as ex:
                    loading.visible = False
                    info.value = f"Không tải được kho font: {ex}"
                self.page.update()

            threading.Thread(target=work, daemon=True).start()

        region.on_change = lambda _: do_search()
        dlg = ft.AlertDialog(
            title=ft.Row(
                [
                    ft.Icon(ft.Icons.CLOUD_DOWNLOAD_ROUNDED, color=COLORS["accent"]),
                    ft.Text("Kho font online — Google Fonts", weight=ft.FontWeight.BOLD),
                ],
                spacing=10,
            ),
            content=ft.Container(
                width=560,
                height=560,
                content=ft.Column(
                    [
                        ft.Text(
                            "Lọc theo ngôn ngữ để lấy font đủ ký tự. Cài xong dùng được trong mọi ô chọn Font.",
                            size=12,
                            color=COLORS["text_secondary"],
                        ),
                        ft.Row([region, search], spacing=10),
                        ft.Row([loading, info], spacing=10),
                        ft.Container(content=result_list, expand=True),
                    ],
                    spacing=12,
                    tight=True,
                ),
            ),
            actions=[ft.TextButton("Đóng", on_click=lambda _: self.page.close(dlg))],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.open(dlg)
        do_search()

    def _set_status(self, msg):
        self.status.value = msg
        try:
            self.page.update()
        except Exception:
            pass

    def _apply_thumb(self, tid, path):
        try:
            image = self._imgs.get(tid)
            spinner = self._spins.get(tid)
            if path:
                path = str(path)
                self._pngs[tid] = path
            if image is not None and path:
                if image.src:
                    image.src = None
                    self.page.update()
                image.src = path
            if spinner is not None:
                spinner.visible = False
            self.page.update()
        except Exception:
            pass

    def _reload(self):
        self._imgs.clear()
        self._spins.clear()
        self._pngs.clear()
        self._build()
        try:
            self.update()
        except Exception:
            pass

    def _rerender_one(self, tid):
        spinner = self._spins.get(tid)
        if spinner is not None:
            spinner.visible = True
        try:
            self.page.update()
        except Exception:
            pass

        def work():
            from core.templates import render_thumbnail

            self._apply_thumb(
                tid, render_thumbnail(tid, self._aspect, force=True)
            )

        threading.Thread(target=work, daemon=True).start()

    def _ensure_all(self, force=False):
        from core.templates import TEMPLATES, has_thumb, render_thumbnail

        aspect = self._aspect
        todo = [
            template["id"]
            for template in TEMPLATES
            if force or not has_thumb(template["id"], aspect)
        ]
        if not todo:
            return
        self.refresh_btn.disabled = True
        for done, tid in enumerate(todo):
            if aspect != self._aspect:
                return
            self._set_status(
                f"Đang render mẫu {aspect}… ({done}/{len(todo)})"
            )
            path = render_thumbnail(tid, aspect, force=force)
            self._apply_thumb(tid, path)
        self.refresh_btn.disabled = False
        self._set_status(f"✓ Đã render xong mẫu {aspect}.")

    def _rerender_all(self, e):
        self._set_status("Bắt đầu render lại…")
        for spinner in self._spins.values():
            spinner.visible = True
        try:
            self.page.update()
        except Exception:
            pass
        threading.Thread(
            target=lambda: self._ensure_all(force=True), daemon=True
        ).start()
