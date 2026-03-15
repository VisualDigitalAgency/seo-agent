"""
Circuit breaker registry for tracking external API failures.
"""

import asyncio
from dataclasses import dataclass
from typing import Dict

from ._error_handling import CircuitBreaker


@dataclass
class ProviderConfig:
    """Configuration for each API provider."""
    threshold: int = 5
    timeout: float = 60.0


# Default provider configurations
PROVIDER_CONFIGS = {
    "serper": ProviderConfig(threshold=5, timeout=60.0),
    "dataforseo": ProviderConfig(threshold=5, timeout=120.0),
    "gsc": ProviderConfig(threshold=3, timeout=120.0),
    "ga4": ProviderConfig(threshold=3, timeout=120.0),
}

# Global circuit breaker registry
_circuit_breakers: Dict[str, CircuitBreaker] = {}
_breakers_lock = asyncio.Lock()


def get_circuit_breaker(provider: str) -> CircuitBreaker:
    """Get or create a circuit breaker for a provider."""
    if provider not in _circuit_breakers:
        config = PROVIDER_CONFIGS.get(provider, ProviderConfig())
        _circuit_breakers[provider] = CircuitBreaker(
            name=provider,
            threshold=config.threshold,
            timeout=config.timeout
        )
    return _circuit_breakers[provider]


def reset_circuit_breaker(provider: str):
    """Reset a circuit breaker (useful for manual recovery)."""
    if provider in _circuit_breakers:
        _circuit_breakers[provider].state.state = "CLOSED"
        _circuit_breakers[provider].state.failures = 0
        _circuit_breakers[provider].state.last_failure_time = None


def get_all_circuit_breakers() -> Dict[str, CircuitBreaker]:
    """Get all circuit breakers (for debugging/monitoring)."""
    return _circuit_breakers.copy()