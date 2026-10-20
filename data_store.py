from __future__ import annotations

import json
from pathlib import Path

_VALID_OVERRIDE = {"auto", "on", "off"}


class DataStore:
    def __init__(self, path: Path):
        self.path = Path(path)
        self._subscriptions: list[str] = []
        self._override: str = "auto"

    def load(self) -> None:
        if not self.path.exists():
            self._subscriptions = []
            self._override = "auto"
            self.save()
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError, UnicodeDecodeError, ValueError):
            data = None
        if not isinstance(data, dict):
            self._subscriptions = []
            self._override = "auto"
            self.save()
            return
        subs = data.get("subscriptions", [])
        self._subscriptions = [str(s) for s in subs] if isinstance(subs, list) else []
        override = data.get("override", "auto")
        self._override = (
            override
            if isinstance(override, str) and override in _VALID_OVERRIDE
            else "auto"
        )

    @property
    def subscriptions(self) -> list[str]:
        return list(self._subscriptions)

    @property
    def override(self) -> str:
        return self._override

    def subscribe(self, umo: str) -> bool:
        umo = str(umo).strip()
        if not umo or umo in self._subscriptions:
            return False
        self._subscriptions.append(umo)
        self.save()
        return True

    def unsubscribe(self, umo: str) -> bool:
        umo = str(umo).strip()
        if umo not in self._subscriptions:
            return False
        self._subscriptions.remove(umo)
        self.save()
        return True

    def set_override(self, state: str) -> None:
        self._override = state if state in _VALID_OVERRIDE else "auto"
        self.save()

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"subscriptions": self._subscriptions, "override": self._override}
        self.path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
