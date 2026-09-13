"""IVERI AI Agent — Sovereign Firewall.

Application-level policy enforcement for air-gapped and sovereign operations.
Enforces network restrictions, process sandboxing boundaries, and data-leak prevention.
"""

import ipaddress
import logging
from dataclasses import dataclass, field
from typing import Optional, Set

from sovereign.network_monitor import (
    NetworkEvent,
    NetworkMode,
    SovereignNetworkMonitor,
    activate_sovereign_mode,
    deactivate_sovereign_mode,
    get_monitor,
)

logger = logging.getLogger(__name__)


@dataclass
class FirewallPolicy:
    """Configurable security policy for sovereign deployments."""
    mode: NetworkMode = NetworkMode.AIR_GAPPED
    allowed_hostnames: Set[str] = field(default_factory=lambda: {"localhost", "127.0.0.1", "::1"})
    allowed_ports: Set[int] = field(default_factory=lambda: {11434, 8080, 7000, 7860, 8000})  # Ollama, llama-server, etc.
    allowed_subnets: list[str] = field(default_factory=lambda: ["127.0.0.0/8", "10.0.0.0/8", "192.168.0.0/16"])
    block_all_outbound_telemetry: bool = True
    strict_raise_exceptions: bool = True


class SovereignFirewall:
    """Application-level firewall enforcing air-gapped sovereign isolation."""

    def __init__(self, policy: Optional[FirewallPolicy] = None):
        self.policy = policy or FirewallPolicy()
        self._monitor: Optional[SovereignNetworkMonitor] = None

    def enable(self) -> SovereignNetworkMonitor:
        """Activate the sovereign firewall and hook into socket layer."""
        self._monitor = activate_sovereign_mode(
            mode=self.policy.mode,
            whitelist=list(self.policy.allowed_hostnames)
        )
        logger.info(
            "Sovereign Firewall ENABLED [Mode: %s | Strict: %s]",
            self.policy.mode.value,
            self.policy.strict_raise_exceptions,
        )
        return self._monitor

    def disable(self) -> None:
        """Deactivate firewall and release socket hooks."""
        deactivate_sovereign_mode()
        self._monitor = None
        logger.info("Sovereign Firewall DISABLED")

    @property
    def is_active(self) -> bool:
        """Whether the firewall is currently active."""
        monitor = get_monitor()
        return monitor is not None and monitor._active

    def audit_summary(self) -> dict:
        """Return the current audit telemetry."""
        monitor = get_monitor()
        if not monitor:
            return {"active": False, "status": "Firewall inactive"}
        return monitor.get_audit_report()


# Global firewall instance
_global_firewall = SovereignFirewall()


def get_firewall() -> SovereignFirewall:
    """Return global singleton firewall."""
    return _global_firewall


def enable_sovereign_firewall(mode: NetworkMode = NetworkMode.AIR_GAPPED) -> SovereignFirewall:
    """Convenience helper to activate sovereign firewall."""
    fw = get_firewall()
    fw.policy.mode = mode
    fw.enable()
    return fw
