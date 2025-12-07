"""Milvus connection pool with reuse, health checks, and auto-reconnect."""
from __future__ import annotations

import threading
import time
from typing import Dict, Optional, Tuple

from app.config.project_config import MilvusConfig
from app.utils.logger import get_logger

logger = get_logger(__name__)

try:
    from pymilvus import connections, utility

    HAS_MILVUS = True
except ImportError:  # pragma: no cover - optional dependency at runtime
    HAS_MILVUS = False


class MilvusConnectionPool:
    """Manage reusable Milvus connections keyed by connection parameters."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._aliases: Dict[Tuple, str] = {}
        self._last_used: Dict[str, float] = {}
        self._max_idle_seconds = 10 * 60  # soft idle expiry

    def get_alias(self, config: MilvusConfig) -> Optional[str]:
        """Get or create a connection alias for the given config."""
        if not HAS_MILVUS:
            logger.error("pymilvus is not installed; cannot create connections")
            return None

        key = self._make_key(config)
        with self._lock:
            alias = self._aliases.get(key)
            if alias:
                if self._is_healthy(alias):
                    self._last_used[alias] = time.time()
                    return alias
                # unhealthy: drop and recreate
                self._disconnect(alias)
                self._aliases.pop(key, None)

            alias = self._create_connection(config)
            if alias:
                self._aliases[key] = alias
                self._last_used[alias] = time.time()
            return alias

    def close_all(self) -> None:
        """Close all connections."""
        with self._lock:
            aliases = list(self._aliases.values())
            for alias in aliases:
                self._disconnect(alias)
            self._aliases.clear()
            self._last_used.clear()

    # Internal helpers -----------------------------------------------------------
    def _make_key(self, config: MilvusConfig) -> Tuple:
        return (
            config.host,
            config.port,
            config.user or "",
            config.password or "",
            getattr(config, "database", "") or "",
        )

    def _is_healthy(self, alias: str) -> bool:
        """Check if a connection alias appears healthy."""
        try:
            if hasattr(connections, "has_connection"):
                if not connections.has_connection(alias):
                    return False
            # Soft idle expiry: reconnect if idle too long
            last_used = self._last_used.get(alias, 0)
            if time.time() - last_used > self._max_idle_seconds:
                return False
            # Lightweight check: list collections to ensure connectivity
            if hasattr(utility, "list_collections"):
                utility.list_collections(using=alias)
            return True
        except Exception as exc:  # pragma: no cover - depends on external service
            logger.warning(f"Milvus connection unhealthy for alias={alias}: {exc}")
            return False

    def _create_connection(self, config: MilvusConfig) -> Optional[str]:
        """Establish a new connection and return its alias."""
        alias = f"pool-{hash((config.host, config.port, time.time()))}"
        try:
            connections.connect(
                alias=alias,
                host=config.host,
                port=config.port,
                user=config.user or None,
                password=config.password or None,
                db_name=getattr(config, "database", None) or None,
            )
            logger.info(
                "Connected to Milvus",
                extra={
                    "alias": alias,
                    "host": config.host,
                    "port": config.port,
                    "database": getattr(config, "database", None),
                },
            )
            return alias
        except Exception as exc:  # pragma: no cover - external service
            logger.error(f"Failed to connect to Milvus at {config.host}:{config.port}: {exc}")
            return None

    def _disconnect(self, alias: str) -> None:
        """Disconnect and cleanup a connection alias."""
        try:
            connections.disconnect(alias)
        except Exception:
            pass


# Convenience singleton
milvus_connection_pool = MilvusConnectionPool()

