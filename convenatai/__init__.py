"""
convenatAI — Lazy-init package.
Submodules are imported on-demand to avoid crashing on missing optional deps
(Circle Python SDK is deprecated, and the `genlayer` CLI OOMs on 256MB VMs).
Use the individual submodules directly instead of importing from this package.
"""
from __future__ import annotations

# We don't import submodules here anymore. Each module has its own try/except
# guards for optional deps. Import directly what you need:
#
#   from convenatai.agent import Agent, Wallet
#   from convenatai.arc_integration import ArcJobManager
#   from convenatai.network import AgentRegistry, MessageBus
#   etc.
#
# This avoids crashing the whole package when one optional dep is missing.

__all__: list[str] = []
