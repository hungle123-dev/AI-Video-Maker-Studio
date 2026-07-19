"""UI quản lý key AI do người dùng nhập và local proxy."""

import logging
import threading

import flet as ft

from ui.theme import COLORS


log = logging.getLogger("TubeCraft.Keys")


class KeysView(ft.Column):
    def __init__(self, page: ft.Page):
        super().__init__(spacing=14, expand=True, alignment=ft.MainAxisAlignment.START)
        self.page = page
        self.body = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO, expand=True)
        self.controls = [
            ft.Row(
                [
                    ft.Text(
                        "Key AI Cloud",
                        size=24,
                        weight=ft.FontWeight.BOLD,
                        color=COLORS["text"],
                    ),
                    ft.Container(expand=True),
                    ft.FilledButton(
                        "Thêm key", icon=ft.Icons.ADD_ROUNDED, on_click=self._add_dialog
                    ),
                ]
            ),
            ft.Text(
                "Key được mã hoá gắn máy khi lưu. Khi gọi AI, key xoay vòng tự động; "
                "key dính quota sẽ tự nghỉ 15 phút.",
                size=12,
                color=COLORS["text_secondary"],
            ),
            self.body,
        ]
        self._reload()

    def _reload(self):
        from core.key_manager import key_manager

        self.body.controls.clear()
        providers = key_manager.list_providers()
        llm = [p for p in providers if p.get("kind") == "llm"]
        tts = [p for p in providers if p.get("kind") == "tts"]

        self.body.controls.append(
            self._group_header("🧠 API nội dung", "Dùng để AI sinh kịch bản bài học")
        )
        self.body.controls.extend(self._provider_card(provider) for provider in llm)
        self.body.controls.append(
            self._group_header("🔊 API giọng đọc (TTS)", "Dùng để tạo giọng đọc cho video")
        )
        self.body.controls.extend(self._provider_card(provider) for provider in tts)
        try:
            self.update()
        except Exception:
            pass

    def _group_header(self, title, subtitle):
        return ft.Container(
            padding=ft.padding.only(top=8, bottom=2),
            content=ft.Column(
                [
                    ft.Text(
                        title,
                        size=15,
                        weight=ft.FontWeight.BOLD,
                        color=COLORS["accent_2"],
                    ),
                    ft.Text(subtitle, size=11, color=COLORS["text_secondary"]),
                ],
                spacing=1,
            ),
        )

    def _provider_card(self, prov):
        from core.key_manager import key_manager

        ready = prov["ready"]
        key_rows = []
        if prov.get("is_local"):
            key_rows.append(self._local_status_row(prov))

        for key in key_manager.list_keys(prov["id"]):
            state_txt, state_color = "hoạt động", COLORS["green"]
            if key["cooling"]:
                state_txt = f"nghỉ {key['cooldown_left'] // 60}p"
                state_color = COLORS["yellow"]
            elif not key["active"]:
                state_txt, state_color = "đã tắt", COLORS["red"]

            actions = []
            if key["source"] == "local":
                actions = [
                    ft.IconButton(
                        ft.Icons.PLAY_CIRCLE_OUTLINE,
                        icon_size=17,
                        tooltip="Test key",
                        on_click=lambda _, p=prov["id"], label=key["label"]: self._test(
                            p, label
                        ),
                    ),
                    ft.Switch(
                        value=key["active"],
                        scale=0.7,
                        on_change=lambda e, p=prov["id"], label=key["label"]: self._toggle(
                            p, label, e.control.value
                        ),
                    ),
                    ft.IconButton(
                        ft.Icons.DELETE_OUTLINE,
                        icon_size=17,
                        icon_color=COLORS["red"],
                        tooltip="Xoá",
                        on_click=lambda _, p=prov["id"], label=key["label"]: self._remove(
                            p, label
                        ),
                    ),
                ]
            key_rows.append(
                ft.Row(
                    [
                        ft.Text(key["label"], size=12, color=COLORS["text"], width=110),
                        ft.Text(
                            key["masked"],
                            size=12,
                            color=COLORS["text_secondary"],
                            width=160,
                            font_family="Consolas",
                        ),
                        ft.Text(state_txt, size=11, color=state_color, width=90),
                        ft.Text(
                            key.get("status_msg", "")[:40],
                            size=11,
                            color=COLORS["text_secondary"],
                            expand=True,
                        ),
                        *actions,
                    ],
                    spacing=8,
                )
            )

        env = " · env ✓" if prov.get("has_env") else ""
        header = ft.Container(
            border_radius=8,
            padding=ft.padding.symmetric(vertical=6, horizontal=8),
            ink=True,
            tooltip=f"Quản lý key {prov['name']} (thêm nhiều key xoay tua)",
            on_click=lambda _, pid=prov["id"]: self._manage_dialog(pid),
            content=ft.Row(
                [
                    ft.Container(
                        width=10,
                        height=10,
                        border_radius=5,
                        bgcolor=COLORS["green"] if ready else COLORS["red"],
                    ),
                    ft.Text(
                        prov["name"],
                        size=15,
                        weight=ft.FontWeight.BOLD,
                        color=COLORS["text"],
                    ),
                    ft.Text(f"({prov['id']})", size=12, color=COLORS["text_secondary"]),
                    ft.Container(expand=True),
                    ft.Text(
                        f"local {prov['local_usable']}/{prov['local_total']}{env}",
                        size=11,
                        color=COLORS["text_secondary"],
                    ),
                    ft.TextButton(
                        "Quản lý key",
                        icon=ft.Icons.KEY_ROUNDED,
                        style=ft.ButtonStyle(
                            color=COLORS["accent"],
                            padding=ft.padding.symmetric(horizontal=8, vertical=0),
                        ),
                        on_click=lambda _, pid=prov["id"]: self._manage_dialog(pid),
                    ),
                ],
                spacing=8,
            ),
        )
        return ft.Container(
            bgcolor=COLORS["bg_card"],
            border_radius=12,
            padding=16,
            border=ft.border.all(1, COLORS["border"]),
            content=ft.Column([header, *key_rows], spacing=10),
        )

    def _local_status_row(self, prov):
        status = ft.Text("Đang kiểm tra...", size=12, color=COLORS["text_secondary"])
        models_txt = ft.Text(
            "", size=11, color=COLORS["text_secondary"], max_lines=2, expand=True
        )

        def probe():
            from core.key_manager import key_manager

            result = key_manager.probe_local(prov["id"])
            if result["running"]:
                status.value = f"🟢 đang chạy · {result['model_count']} model"
                status.color = COLORS["green"]
                models_txt.value = ", ".join(result["models"][:6])
            else:
                status.value = "🔴 không phản hồi"
                status.color = COLORS["red"]
                models_txt.value = (
                    "Mở 9Router trên máy (cổng 20128). Key là tuỳ chọn — "
                    "không có key vẫn gọi được."
                )
            try:
                self.page.update()
            except Exception:
                pass

        threading.Thread(target=probe, daemon=True).start()
        return ft.Row(
            [
                status,
                models_txt,
                ft.IconButton(
                    ft.Icons.REFRESH_ROUNDED,
                    icon_size=16,
                    tooltip="Kiểm tra lại",
                    on_click=lambda _: threading.Thread(target=probe, daemon=True).start(),
                ),
            ],
            spacing=10,
        )

    def _snack(self, msg):
        self.page.open(ft.SnackBar(content=ft.Text(msg)))

    def _add_dialog(self, e=None, prov_id=None):
        from core.key_manager import PROVIDERS

        start = prov_id if prov_id in PROVIDERS else "gemini"
        provider = ft.Dropdown(
            label="Provider",
            value=start,
            options=[ft.dropdown.Option(pid, info["name"]) for pid, info in PROVIDERS.items()],
        )
        key = ft.TextField(label="API key", password=True, can_reveal_password=True)
        label = ft.TextField(label="Nhãn (tuỳ chọn)", hint_text="vd: key-cty")

        def add(_):
            from core.key_manager import key_manager

            result = key_manager.add_key(provider.value, key.value, label.value.strip())
            self.page.close(dlg)
            self._snack(result["message"])
            self._reload()

        title = f"Thêm key · {PROVIDERS[start]['name']}" if prov_id else "Thêm key AI"
        dlg = ft.AlertDialog(
            title=ft.Text(title),
            content=ft.Column([provider, key, label], tight=True, width=420),
            actions=[
                ft.TextButton("Huỷ", on_click=lambda _: self.page.close(dlg)),
                ft.FilledButton("Thêm", on_click=add),
            ],
        )
        self.page.open(dlg)

    def _manage_dialog(self, prov_id):
        log.info("_manage_dialog CLICK prov=%s", prov_id)
        try:
            self.__manage_dialog(prov_id)
        except Exception:
            log.exception("_manage_dialog FAILED prov=%s", prov_id)
            self._snack("Lỗi mở quản lý key (xem log).")

    def __manage_dialog(self, prov_id):
        from core.key_manager import PROVIDERS, key_manager

        provider = next(
            (item for item in key_manager.list_providers() if item["id"] == prov_id), None
        )
        if provider is None:
            return
        name = PROVIDERS.get(prov_id, {}).get("name", prov_id)
        key_list = ft.Column(spacing=8, tight=True, scroll=ft.ScrollMode.AUTO, height=220)
        new_key = ft.TextField(
            label="API key mới",
            password=True,
            can_reveal_password=True,
            expand=True,
            dense=True,
        )
        new_label = ft.TextField(
            label="Nhãn", hint_text="tự đặt nếu trống", width=140, dense=True
        )

        def refresh_list():
            key_list.controls.clear()
            keys = key_manager.list_keys(prov_id)
            if not keys:
                key_list.controls.append(
                    ft.Text(
                        "Chưa có key nào. Thêm ít nhất 1 key bên dưới.",
                        size=12,
                        color=COLORS["text_secondary"],
                    )
                )
            for key in keys:
                state_txt, state_color = "hoạt động", COLORS["green"]
                if key["cooling"]:
                    state_txt = f"nghỉ {key['cooldown_left'] // 60}p"
                    state_color = COLORS["yellow"]
                elif not key["active"]:
                    state_txt, state_color = "đã tắt", COLORS["red"]

                actions = []
                if key["source"] == "local":
                    actions = [
                        ft.IconButton(
                            ft.Icons.PLAY_CIRCLE_OUTLINE,
                            icon_size=18,
                            tooltip="Test key",
                            on_click=lambda _, label=key["label"]: self._test_in(
                                prov_id, label
                            ),
                        ),
                        ft.Switch(
                            value=key["active"],
                            scale=0.7,
                            tooltip="Bật/tắt xoay tua key này",
                            on_change=lambda e, label=key["label"]: (
                                key_manager.set_active(prov_id, label, e.control.value),
                                refresh_list(),
                                self.page.update(),
                            ),
                        ),
                        ft.IconButton(
                            ft.Icons.DELETE_OUTLINE,
                            icon_size=18,
                            icon_color=COLORS["red"],
                            tooltip="Xoá",
                            on_click=lambda _, label=key["label"]: (
                                key_manager.remove_key(prov_id, label),
                                refresh_list(),
                                self._reload(),
                                self.page.update(),
                            ),
                        ),
                    ]
                key_list.controls.append(
                    ft.Container(
                        bgcolor=COLORS["bg_glass"],
                        border_radius=8,
                        padding=ft.padding.symmetric(horizontal=10, vertical=4),
                        content=ft.Row(
                            [
                                ft.Text(
                                    key["label"], size=12, color=COLORS["text"], width=90
                                ),
                                ft.Text(
                                    key["masked"],
                                    size=12,
                                    font_family="Consolas",
                                    color=COLORS["text_secondary"],
                                    expand=True,
                                ),
                                ft.Text(state_txt, size=11, color=state_color, width=74),
                                *actions,
                            ],
                            spacing=6,
                        ),
                    )
                )

        def add(_):
            if not new_key.value.strip():
                self._snack("Nhập API key trước.")
                return
            result = key_manager.add_key(prov_id, new_key.value, new_label.value.strip())
            self._snack(result["message"])
            new_key.value = ""
            new_label.value = ""
            refresh_list()
            self._reload()
            self.page.update()

        refresh_list()
        body = ft.Column(
            [
                ft.Text(
                    "Thêm nhiều key để tự xoay tua: khi một key lỗi hoặc hết quota, "
                    "hệ thống chuyển sang key kế tiếp.",
                    size=12,
                    color=COLORS["text_secondary"],
                ),
                key_list,
                ft.Divider(height=1, color=COLORS["border"]),
                ft.Row(
                    [
                        new_key,
                        new_label,
                        ft.FilledButton(
                            "Thêm", icon=ft.Icons.ADD_ROUNDED, on_click=add
                        ),
                    ],
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ],
            spacing=12,
            tight=True,
            width=560,
        )
        dlg = ft.AlertDialog(
            title=ft.Row(
                [
                    ft.Icon(ft.Icons.KEY_ROUNDED, color=COLORS["accent"]),
                    ft.Text(f"Quản lý key · {name}", weight=ft.FontWeight.BOLD),
                ],
                spacing=8,
            ),
            content=body,
            actions=[ft.TextButton("Đóng", on_click=lambda _: self.page.close(dlg))],
        )
        self._dlg = dlg
        self.page.open(dlg)

    def _test_in(self, provider, label):
        self._snack(f"Đang test {provider}/{label}...")

        def work():
            from core.key_manager import key_manager

            self._snack(key_manager.test_key(provider, label)["message"])

        threading.Thread(target=work, daemon=True).start()

    def _test(self, provider, label):
        self._snack(f"Đang test {provider}/{label}...")

        def work():
            from core.key_manager import key_manager

            self._snack(key_manager.test_key(provider, label)["message"])
            self._reload()

        threading.Thread(target=work, daemon=True).start()

    def _toggle(self, provider, label, active):
        from core.key_manager import key_manager

        key_manager.set_active(provider, label, active)
        self._reload()

    def _remove(self, provider, label):
        from core.key_manager import key_manager

        key_manager.remove_key(provider, label)
        self._reload()
