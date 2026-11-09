"""2026-07-28 ↔ 2025-11-25 capability degradation helpers.

All newer-protocol features must degrade gracefully (§12). This module maps a
negotiated protocol version to the feature gates a tool may rely on.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FeatureGates:
    version: str
    stateless_http: bool
    server_discover: bool
    mrtr_input_required: bool  # InputRequiredResult multi-round confirmation
    elicitation: bool  # 2025-11-25 server-initiated elicitation
    subscriptions_listen: bool
    tasks_extension: bool

    @property
    def is_modern(self) -> bool:
        return self.version >= "2026-07-28"


def gates_for(version: str) -> FeatureGates:
    modern = version >= "2026-07-28"
    return FeatureGates(
        version=version,
        stateless_http=modern,
        server_discover=True,  # both eras negotiate; we always implement
        mrtr_input_required=modern,
        elicitation=not modern,  # pre-2026-07-28 server-initiated elicitation
        subscriptions_listen=modern,
        tasks_extension=True,  # 2025-11-25 experimental → 2026-07-28 official ext
    )
