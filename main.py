from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, MessageChain, filter
from astrbot.api.provider import Provider
from astrbot.api.star import Context, Star, StarTools
from astrbot.core.config.astrbot_config import AstrBotConfig

from .config_defaults import (
    get_bool,
    get_list,
    get_notice,
    get_peak_action,
    get_str,
    get_transition_notice,
    get_windows_raw,
)
from .data_store import DataStore
from .notifier import (
    Target,
    classify_image,
    format_dt,
    parse_target,
    render_text,
    should_notify,
)
from .peak_schedule import (
    PeakWindow,
    active_window,
    is_peak,
    next_boundaries,
    next_transition,
    parse_windows,
)
from .provider_match import is_affected
from .whitelist import check_whitelist

_PLUGIN_NAME = "astrbot_plugin_peak_guard"


class PeakGuard(Star):
    def __init__(self, context: Context, config: AstrBotConfig | None = None):
        super().__init__(context)
        self.config = config if config is not None else {}
        data_dir = StarTools.get_data_dir(_PLUGIN_NAME)
        self.store = DataStore(data_dir / "state.json")
        self.store.load()
        self._scheduler_task: asyncio.Task | None = None
        self._wake = asyncio.Event()
        self._last_peak: bool | None = None
        self._windows: list[PeakWindow] = []
        self._targets: list[Target] = []
        self._warned_providers: set[str] = set()
        self._reload()

    # ---------- 配置与状态 ----------
    def _reload(self) -> None:
        self.tz_name = get_str(self.config, "timezone", "Asia/Shanghai")
        try:
            self._tz = ZoneInfo(self.tz_name)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                f"[PeakGuard] 无效时区 {self.tz_name!r}（{exc}），回退 UTC+8"
            )
            self._tz = timezone(timedelta(hours=8))
        self._windows = parse_windows(
            get_windows_raw(self.config),
            on_skip=lambda m: logger.warning(f"[PeakGuard] 跳过无效时段：{m}"),
        )
        if not self._windows:
            logger.warning("[PeakGuard] 未解析出任何有效高峰时段")
        self.allow_admins = get_bool(self.config, "allow_admins", True)
        self.whitelist_users = get_list(self.config, "whitelist_users")
        self.whitelist_groups = get_list(self.config, "whitelist_groups")
        self.block_image = get_str(self.config, "block_image", "").strip()
        self.at_sender = get_bool(self.config, "at_sender", False)
        self.peak_action = get_peak_action(self.config)
        self.peak_provider_id = get_str(self.config, "peak_provider_id", "").strip()
        self.affected_providers = get_str(self.config, "affected_providers", "*")
        self.gate_when_provider_unknown = get_bool(
            self.config, "gate_when_provider_unknown", True
        )
        self._warned_providers = set()
        self._targets = []
        for raw in get_list(self.config, "notify_targets"):
            target = parse_target(str(raw))
            if target is None:
                logger.warning(f"[PeakGuard] 无法解析提醒目标：{raw!r}")
            else:
                self._targets.append(target)

    def _now(self) -> datetime:
        return datetime.now(self._tz)

    def _is_peak_now(self) -> bool:
        override = self.store.override
        if override == "on":
            return True
        if override == "off":
            return False
        return is_peak(self._now(), self._windows)

    def _wake_scheduler(self) -> None:
        self._wake.set()

    def _boundary_texts(self, now: datetime) -> tuple[str, str]:
        override = self.store.override
        if override == "on":
            return "手动恢复时（/峰谷强制 auto）", "手动恢复后按计划"
        if override == "off":
            return "当前未拦截", "手动恢复后按计划"
        next_off, next_peak = next_boundaries(now, self._windows)
        return format_dt(next_off), format_dt(next_peak)

    def _build_context(self, now: datetime) -> dict[str, str]:
        next_off, next_peak = self._boundary_texts(now)
        win = active_window(now, self._windows)
        return {
            "time": now.strftime("%Y-%m-%d %H:%M"),
            "tz": self.tz_name,
            "next_off": next_off,
            "next_peak": next_peak,
            "start": win.raw_start if win else "未知",
            "end": win.raw_end if win else "未知",
            "action": "切换模型" if self.peak_action == "switch" else "暂停对话",
        }

    def _notice_chain(
        self,
        text: str,
        *,
        at_sender_id: str | None = None,
        at_sender_name: str = "",
    ) -> MessageChain:
        chain = MessageChain()
        if at_sender_id:
            chain.at(at_sender_name, at_sender_id)
        chain.message(text)
        return chain

    def _image_chain(self) -> MessageChain | None:
        image_kind = classify_image(self.block_image)
        if image_kind == "url":
            return MessageChain().url_image(self.block_image)
        if image_kind == "file":
            if Path(self.block_image).exists():
                return MessageChain().file_image(self.block_image)
            logger.warning(f"[PeakGuard] 提示图片不存在：{self.block_image}")
        return None

    # ---------- 供应商识别 ----------
    async def _current_provider(
        self, event: AstrMessageEvent
    ) -> tuple[str, object | None]:
        provider_id = ""
        try:
            selected = event.get_extra("selected_provider")
            if isinstance(selected, str) and selected.strip():
                provider_id = selected.strip()
        except Exception:  # noqa: BLE001
            pass
        if not provider_id:
            try:
                provider_id = str(
                    await self.context.get_current_chat_provider_id(
                        umo=event.unified_msg_origin
                    )
                    or ""
                ).strip()
            except Exception as exc:  # noqa: BLE001
                logger.debug(f"[PeakGuard] 获取当前 Provider 失败：{exc}")
                provider_id = ""
        provider = None
        if provider_id:
            try:
                provider = self.context.get_provider_by_id(provider_id)
            except Exception as exc:  # noqa: BLE001
                logger.debug(f"[PeakGuard] 查询 Provider {provider_id!r} 失败：{exc}")
                provider = None
        if provider is None:
            provider_id = ""
        return provider_id, provider

    def _provider_affected(self, provider_id: str, provider: object | None) -> bool:
        meta_id = meta_model = meta_type = ""
        if provider is not None:
            try:
                meta = provider.meta()
                meta_id = str(getattr(meta, "id", "") or "")
                meta_model = str(getattr(meta, "model", "") or "")
                meta_type = str(getattr(meta, "type", "") or "")
            except Exception:  # noqa: BLE001
                pass
        return is_affected(
            self.affected_providers,
            provider_id=provider_id,
            meta_id=meta_id,
            meta_model=meta_model,
            meta_type=meta_type,
            unknown_allowed=self.gate_when_provider_unknown,
        )

    def _provider_display(self, provider_id: str, provider: object | None) -> str:
        if not provider_id:
            return "未识别"
        if provider is not None:
            try:
                meta = provider.meta()
                model = str(getattr(meta, "model", "") or "")
                ptype = str(getattr(meta, "type", "") or "")
                if model:
                    return f"{model}（{ptype or '未知'}）"
            except Exception:  # noqa: BLE001
                pass
        return provider_id

    def _warn_once(self, key: str, message: str) -> None:
        if key in self._warned_providers:
            return
        self._warned_providers.add(key)
        logger.warning(f"[PeakGuard] {message}")

    async def _apply_switch(self, event: AstrMessageEvent) -> bool:
        target = self.peak_provider_id
        if not target:
            self._warn_once(
                "<empty>",
                "高峰动作设置为 switch，但未配置 peak_provider_id，将改为暂停对话",
            )
            return False
        provider = None
        try:
            provider = self.context.get_provider_by_id(target)
        except Exception as exc:  # noqa: BLE001
            logger.debug(f"[PeakGuard] 查询高峰 Provider {target!r} 失败：{exc}")
        if provider is None:
            self._warn_once(target, f"高峰 Provider {target!r} 不存在，将改为暂停对话")
            return False
        if not isinstance(provider, Provider):
            self._warn_once(
                target,
                f"高峰 Provider {target!r} 不是对话模型（{type(provider).__name__}），将改为暂停对话",
            )
            return False
        event.set_extra("selected_provider", target)
        return True

    # ---------- 拦截 ----------
    async def _should_gate(self, event: AstrMessageEvent) -> bool:
        if not get_bool(self.config, "enabled", True):
            return False
        if not self._is_peak_now():
            return False
        group_id = event.get_group_id()
        if check_whitelist(
            event.get_sender_id(),
            group_id,
            self.whitelist_users,
            self.whitelist_groups,
            is_admin=event.is_admin(),
            allow_admins=self.allow_admins,
        ):
            return False
        provider_id, provider = await self._current_provider(event)
        return self._provider_affected(provider_id, provider)

    async def _pause(self, event: AstrMessageEvent) -> None:
        try:
            text = render_text(
                get_notice(self.config, "block_notice"),
                self._build_context(self._now()),
            )
            at_id = None
            at_name = ""
            if self.at_sender and event.get_group_id():
                at_id = event.get_sender_id()
                at_name = event.get_sender_name()
            try:
                await event.send(
                    self._notice_chain(
                        text, at_sender_id=at_id, at_sender_name=at_name
                    )
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"[PeakGuard] 发送拦截提示失败：{exc}")
            try:
                image_chain = self._image_chain()
                if image_chain is not None:
                    await event.send(image_chain)
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"[PeakGuard] 发送拦截提示图片失败：{exc}")
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"[PeakGuard] 构建或发送拦截提示失败：{exc}")
        finally:
            event.stop_event()

    @filter.on_waiting_llm_request()
    async def on_waiting_llm(self, event: AstrMessageEvent):
        """switch 必须在 build_main_agent 之前设置 selected_provider。"""
        if self.peak_action != "switch":
            return
        if not await self._should_gate(event):
            return
        await self._apply_switch(event)

    @filter.on_llm_request()
    async def on_llm_request(self, event: AstrMessageEvent, _request=None):
        """pause 使用 OnLLMRequestEvent：该钩子自 4.20.0 起即可中止请求。"""
        if self.peak_action == "switch":
            if not await self._should_gate(event):
                return
            if await self._apply_switch(event):
                return
        elif not await self._should_gate(event):
            return
        await self._pause(event)

    # ---------- 指令 ----------
    def _deny(self, event: AstrMessageEvent):
        return event.plain_result("❌ 该指令仅限管理员使用")

    @filter.command("峰谷状态")
    async def cmd_status(self, event: AstrMessageEvent):
        """查看峰谷守卫状态"""
        if not event.is_admin():
            yield self._deny(event)
            return
        now = self._now()
        next_off_text, next_peak_text = self._boundary_texts(now)
        enabled = get_bool(self.config, "enabled", True)
        override = self.store.override
        peak = self._is_peak_now()
        lines = [
            "【峰谷守卫状态】",
            f"插件开关：{'开' if enabled else '关'}",
            f"时区：{self.tz_name}（当前 {now.strftime('%Y-%m-%d %H:%M')}）",
            f"是否高峰期：{'是' if peak else '否'}",
            f"手动覆盖：{override}",
            f"高峰动作：{'切换模型' if self.peak_action == 'switch' else '暂停对话'}",
        ]
        if self.peak_action == "switch":
            lines.append(f"高峰 Provider：{self.peak_provider_id or '未配置'}")
        provider_id, provider = await self._current_provider(event)
        lines.append(f"当前供应商：{self._provider_display(provider_id, provider)}")
        affected = self.affected_providers.strip()
        affected_label = "全部" if "*" in affected else (affected or "不拦截")
        lines.append(f"受影响供应商：{affected_label}")
        if peak:
            lines.append(f"下一次离开高峰：{next_off_text}")
        lines.append(f"下一次进入高峰：{next_peak_text}")
        lines.append(f"提醒目标：静态 {len(self._targets)} 个 / 订阅 {len(self.store.subscriptions)} 个")
        yield event.plain_result("\n".join(lines))

    @filter.command("峰谷强制")
    async def cmd_force(self, event: AstrMessageEvent):
        """手动覆盖：/峰谷强制 on|off|auto"""
        if not event.is_admin():
            yield self._deny(event)
            return
        parts = (event.message_str or "").split()
        mode = parts[1].lower() if len(parts) > 1 else ""
        if len(parts) != 2 or mode not in ("on", "off", "auto"):
            yield event.plain_result("用法：/峰谷强制 on（强制暂停）| off（强制恢复）| auto（跟随时段）")
            return
        self.store.set_override(mode)
        self._wake_scheduler()
        mapping = {"on": "强制暂停（拦截对话）", "off": "强制恢复（放行对话）", "auto": "跟随时段计划"}
        yield event.plain_result(f"✅ 已设置为：{mapping[mode]}")

    @filter.command("峰谷订阅")
    async def cmd_subscribe(self, event: AstrMessageEvent):
        """将当前会话加入高峰提醒目标"""
        if not event.is_admin():
            yield self._deny(event)
            return
        umo = event.unified_msg_origin
        if self.store.subscribe(umo):
            yield event.plain_result("✅ 本会话已加入高峰提醒目标")
        else:
            yield event.plain_result("ℹ️ 本会话已在高峰提醒目标中")

    @filter.command("峰谷退订")
    async def cmd_unsubscribe(self, event: AstrMessageEvent):
        """将当前会话移出高峰提醒目标"""
        if not event.is_admin():
            yield self._deny(event)
            return
        umo = event.unified_msg_origin
        if self.store.unsubscribe(umo):
            yield event.plain_result("✅ 本会话已移出高峰提醒目标")
        else:
            yield event.plain_result("ℹ️ 本会话不在高峰提醒目标中")

    @filter.command("峰谷重载")
    async def cmd_reload(self, event: AstrMessageEvent):
        """重新读取配置并重建时段"""
        if not event.is_admin():
            yield self._deny(event)
            return
        self._reload()
        self._wake_scheduler()
        yield event.plain_result(f"✅ 已重载，当前解析到 {len(self._windows)} 条高峰时段")

    # ---------- 调度与通知 ----------
    async def initialize(self):
        self._start_scheduler()

    def _start_scheduler(self) -> None:
        if self._scheduler_task is None or self._scheduler_task.done():
            self._last_peak = self._is_peak_now()
            self._scheduler_task = asyncio.create_task(self._scheduler_loop())
            logger.info("[PeakGuard] 调度器已启动")

    async def _scheduler_loop(self) -> None:
        while True:
            try:
                now = self._now()
                delay = 60.0
                if self.store.override == "auto":
                    nxt = next_transition(now, self._windows)
                    if nxt is not None:
                        delay = max(1.0, min((nxt - now).total_seconds(), 60.0))
                try:
                    await asyncio.wait_for(self._wake.wait(), timeout=delay)
                except asyncio.TimeoutError:
                    pass
                else:
                    self._wake.clear()
                current = self._is_peak_now()
                if self._last_peak is None:
                    self._last_peak = current
                    continue
                if current != self._last_peak:
                    if should_notify(
                        get_bool(self.config, "enabled", True),
                        current,
                        self._last_peak,
                        get_bool(self.config, "notify_on_enter", True),
                        get_bool(self.config, "notify_on_exit", True),
                    ):
                        await self._send_transition_notice(current)
                    self._last_peak = current
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"[PeakGuard] 调度循环异常：{exc}")
                await asyncio.sleep(60)

    def _platform_id(self) -> str:
        try:
            for inst in self.context.platform_manager.get_insts():
                meta = inst.meta()
                platform_id = str(getattr(meta, "id", "") or "")
                name = str(getattr(meta, "name", "") or "").lower()
                if "aiocqhttp" in platform_id.lower() or "aiocqhttp" in name:
                    return platform_id or "aiocqhttp"
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"[PeakGuard] 获取平台 ID 失败：{exc}")
        return "aiocqhttp"

    def _target_session(self, target: Target) -> str:
        if target.kind == "umo":
            return target.value
        if target.kind == "group":
            return f"{self._platform_id()}:GroupMessage:{target.value}"
        if target.kind == "private":
            return f"{self._platform_id()}:FriendMessage:{target.value}"
        return target.value

    async def _broadcast(self, text: str) -> None:
        if not text:
            return
        targets = list(self._targets)
        targets += [Target("umo", umo) for umo in self.store.subscriptions]
        seen: set[str] = set()
        for target in targets:
            try:
                session = self._target_session(target)
                if not session:
                    logger.warning(f"[PeakGuard] 跳过无效提醒目标：{target.kind}:{target.value}")
                    continue
                if session in seen:
                    continue
                seen.add(session)
                await self.context.send_message(session, MessageChain().message(text))
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"[PeakGuard] 通知发送失败 {target.kind}:{target.value}：{exc}")

    async def _send_transition_notice(self, now_peak: bool) -> None:
        if not get_bool(self.config, "enabled", True):
            return
        if now_peak:
            if not get_bool(self.config, "notify_on_enter", True):
                return
            text = render_text(
                get_transition_notice(self.config, "enter_notice", self.peak_action),
                self._build_context(self._now()),
            )
        else:
            if not get_bool(self.config, "notify_on_exit", True):
                return
            text = render_text(
                get_transition_notice(self.config, "exit_notice", self.peak_action),
                self._build_context(self._now()),
            )
        logger.info(f"[PeakGuard] 状态切换 -> {'高峰' if now_peak else '空闲'}，发送通知")
        await self._broadcast(text)

    # ---------- 生命周期 ----------
    async def terminate(self):
        try:
            if self._scheduler_task and not self._scheduler_task.done():
                self._scheduler_task.cancel()
                try:
                    await self._scheduler_task
                except asyncio.CancelledError:
                    pass
        finally:
            self._scheduler_task = None
        logger.info("[PeakGuard] 已卸载")
