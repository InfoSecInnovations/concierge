from __future__ import annotations
import asyncio
import ipaddress
import os
import socket
from urllib.parse import urlsplit
from shabti_types import ForbiddenUrlError

ALLOWED_SCHEMES = ("http", "https")
DEFAULT_PORTS = {"http": 80, "https": 443}


def allow_private_networks() -> bool:
    # an on-prem deployment ingesting an internal wiki is a first class use case, but it has to be
    # opted into: the URL is caller supplied and the route only requires the `update` scope
    return os.getenv("SHABTI_CRAWL_ALLOW_PRIVATE_NETWORKS") == "True"


def _rejection_reason(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> str | None:
    """Why this address must not be fetched, or None when it may be."""
    mapped = getattr(ip, "ipv4_mapped", None)
    if mapped:  # ::ffff:127.0.0.1 and friends
        return _rejection_reason(mapped)
    # these stay blocked even when private networks are allowed: link-local covers the cloud
    # metadata endpoints (169.254.169.254), and nothing legitimate is ingested over the others
    if ip.is_loopback:
        return "a loopback address"
    if ip.is_link_local:
        return "a link-local address"
    if ip.is_multicast:
        return "a multicast address"
    if ip.is_unspecified:
        return "an unspecified address"
    if ip.is_reserved:
        return "a reserved address"
    if allow_private_networks():
        return None
    # is_global is False for every private, shared and otherwise non-routable range
    if not ip.is_global:
        return "a private address"
    return None


async def check_url_allowed(url: str) -> None:
    """Raise ForbiddenUrlError unless `url` is safe for the server to fetch.

    Only closes the gap between what the caller asked for and what we resolve it to; a DNS rebind
    between this check and the fetch is not covered.
    """
    parts = urlsplit(url)
    if parts.scheme not in ALLOWED_SCHEMES:
        raise ForbiddenUrlError(
            url=url,
            message=f"only {' and '.join(ALLOWED_SCHEMES)} URLs can be ingested",
        )
    if parts.username or parts.password:
        raise ForbiddenUrlError(
            url=url, message="URLs with embedded credentials cannot be ingested"
        )
    host = parts.hostname
    if not host:
        raise ForbiddenUrlError(url=url, message="URL has no host")
    try:
        port = parts.port or DEFAULT_PORTS[parts.scheme]
    except ValueError as e:
        raise ForbiddenUrlError(url=url, message="URL has an invalid port") from e

    loop = asyncio.get_running_loop()
    try:
        infos = await loop.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror as e:
        raise ForbiddenUrlError(
            url=url, message=f"host {host} could not be resolved"
        ) from e

    # every address the host resolves to has to be acceptable, not just the first one
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        reason = _rejection_reason(ip)
        if reason:
            raise ForbiddenUrlError(
                url=url, message=f"{host} resolves to {ip}, {reason}"
            )


def same_origin(url: str, other: str) -> bool:
    a, b = urlsplit(url), urlsplit(other)
    return (a.scheme, a.hostname, a.port or DEFAULT_PORTS.get(a.scheme)) == (
        b.scheme,
        b.hostname,
        b.port or DEFAULT_PORTS.get(b.scheme),
    )
