"""
Delivery Provider Abstraction — Phase 3D Communication Infrastructure.

Architecture:
  Abstract base classes define the provider contract.
  Concrete implementations are registered in a provider registry.
  Business code calls providers through the registry, never directly.

  This decouples communication delivery from business logic and
  makes the system future queue-ready.

  TODO: Phase 6 — SendGridEmailProvider — when SENDGRID_API_KEY is configured
  TODO: Phase 6 — SESEmailProvider — AWS SES integration
  TODO: Phase 6 — TwilioSMSProvider — Twilio SMS/WhatsApp
  TODO: Phase 6 — WhatsAppBusinessProvider — WhatsApp Business API
  TODO: Phase 6 — FirebasePushProvider — push notifications
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ═════════════════════════════════════════════════════════════════════════════
# Provider Response
# ═════════════════════════════════════════════════════════════════════════════


@dataclass
class ProviderResponse:
    """Standardized response from any delivery provider."""

    provider_id: str
    status: str  # "sent" | "failed"
    raw_response: dict[str, Any] = field(default_factory=dict)
    error_message: str | None = None


# ═════════════════════════════════════════════════════════════════════════════
# Abstract Base Provider
# ═════════════════════════════════════════════════════════════════════════════


class BaseProvider(ABC):
    """Abstract base for all delivery providers."""

    @abstractmethod
    def send(
        self,
        recipient: str,
        subject: str | None,
        body: str,
        attachments: list[dict[str, Any]] | None = None,
    ) -> ProviderResponse:
        """
        Send a message via this provider.

        Args:
            recipient: Email address, phone number, or device token.
            subject: Message subject (email). None for SMS/WhatsApp.
            body: Message body content.
            attachments: Optional list of attachment dicts with keys:
                - filename: str
                - content_type: str
                - content: bytes (base64-encoded for JSON-safe transport)

        Returns:
            ProviderResponse with status and metadata.
        """
        ...


# ═════════════════════════════════════════════════════════════════════════════
# Mock / Local Providers (safe for development)
# ═════════════════════════════════════════════════════════════════════════════


class MockEmailProvider(BaseProvider):
    """
    Mock email provider — logs to console only.

    Safe for development and testing.
    No external dependencies, no network calls.
    """

    def send(
        self,
        recipient: str,
        subject: str | None,
        body: str,
        attachments: list[dict[str, Any]] | None = None,
    ) -> ProviderResponse:
        logger.info(
            "[MOCK EMAIL] To: %s | Subject: %s | Body length: %d chars | Attachments: %s",
            recipient,
            subject or "(no subject)",
            len(body),
            len(attachments) if attachments else 0,
        )
        if attachments:
            for att in attachments:
                logger.info(
                    "  [MOCK EMAIL] Attachment: %s (%s, %d bytes)",
                    att.get("filename", "unknown"),
                    att.get("content_type", "unknown"),
                    len(att.get("content", b"")),
                )
        return ProviderResponse(
            provider_id="mock_email",
            status="sent",
            raw_response={"mock": True, "recipient": recipient},
        )


class MockSMSProvider(BaseProvider):
    """
    Mock SMS provider — logs to console only.

    Safe for development and testing.
    """

    def send(
        self,
        recipient: str,
        subject: str | None,
        body: str,
        attachments: list[dict[str, Any]] | None = None,
    ) -> ProviderResponse:
        logger.info(
            "[MOCK SMS] To: %s | Body: %s",
            recipient,
            body[:160] + ("..." if len(body) > 160 else ""),
        )
        return ProviderResponse(
            provider_id="mock_sms",
            status="sent",
            raw_response={"mock": True, "recipient": recipient},
        )


class MockWhatsAppProvider(BaseProvider):
    """
    Mock WhatsApp provider — logs to console only.

    Safe for development and testing.
    """

    def send(
        self,
        recipient: str,
        subject: str | None,
        body: str,
        attachments: list[dict[str, Any]] | None = None,
    ) -> ProviderResponse:
        logger.info(
            "[MOCK WHATSAPP] To: %s | Body: %s",
            recipient,
            body[:200] + ("..." if len(body) > 200 else ""),
        )
        return ProviderResponse(
            provider_id="mock_whatsapp",
            status="sent",
            raw_response={"mock": True, "recipient": recipient},
        )


class MockInAppProvider(BaseProvider):
    """
    Mock in-app notification provider — logs to console only.

    In-app notifications are stored in the database and retrieved
    by the frontend. This mock logs the delivery for audit purposes.
    """

    def send(
        self,
        recipient: str,
        subject: str | None,
        body: str,
        attachments: list[dict[str, Any]] | None = None,
    ) -> ProviderResponse:
        logger.info(
            "[MOCK IN-APP] User: %s | Subject: %s | Body: %s",
            recipient,
            subject or "(no subject)",
            body[:200] + ("..." if len(body) > 200 else ""),
        )
        return ProviderResponse(
            provider_id="mock_in_app",
            status="sent",
            raw_response={"mock": True, "recipient": recipient},
        )


# ═════════════════════════════════════════════════════════════════════════════
# Provider Registry
# ═════════════════════════════════════════════════════════════════════════════

# Default registry with mock providers
_providers: dict[str, BaseProvider] = {
    "email": MockEmailProvider(),
    "sms": MockSMSProvider(),
    "whatsapp": MockWhatsAppProvider(),
    "in_app": MockInAppProvider(),
}


def get_provider(channel: str) -> BaseProvider:
    """
    Get the registered provider for a channel.

    Args:
        channel: One of "email", "sms", "whatsapp", "in_app"

    Returns:
        The registered provider instance.

    Raises:
        ValueError: If no provider is registered for the channel.
    """
    provider = _providers.get(channel)
    if provider is None:
        raise ValueError(f"No provider registered for channel: {channel}")
    return provider


def register_provider(channel: str, provider: BaseProvider) -> None:
    """
    Register a provider for a channel.

    This allows swapping mock providers with real implementations
    at application startup or via configuration.

    Args:
        channel: Channel name (email, sms, whatsapp, in_app).
        provider: Provider instance implementing BaseProvider.
    """
    _providers[channel] = provider
    logger.info("Registered provider for channel '%s': %s", channel, type(provider).__name__)


def reset_providers() -> None:
    """Reset all providers to mocks — useful for testing."""
    _providers.clear()
    _providers["email"] = MockEmailProvider()
    _providers["sms"] = MockSMSProvider()
    _providers["whatsapp"] = MockWhatsAppProvider()
    _providers["in_app"] = MockInAppProvider()
    logger.info("All providers reset to mocks")
