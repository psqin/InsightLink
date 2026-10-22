"""公开 URL 的入口校验；只解析地址，不下载网页，也不承诺控制 MCP 的内部跳转。"""

import asyncio
import ipaddress
import socket

import httpx


class PublicURLValidationError(ValueError):
    """地址不属于可交给公开工具的 URL，或暂时无法完成公网解析。"""


def _public_address(value: str) -> bool:
    """要求所有 IPv4/IPv6 地址为公网，排除映射、隧道及带作用域的 IPv6。"""
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        return False
    if not address.is_global or address.is_multicast or address.is_unspecified:
        return False
    return not isinstance(address, ipaddress.IPv6Address) or not (
        address.ipv4_mapped or address.sixtofour or address.teredo or address.scope_id
    )


def validate_public_url(value: str) -> httpx.URL:
    """在调用 MCP 前拒绝凭据、非常规协议/端口、内网 IP 及易混淆地址。"""
    if (
        not isinstance(value, str)
        or not value
        or len(value) > 2048
        or any(ord(char) < 33 for char in value)
        or "\\" in value
    ):
        raise PublicURLValidationError("网页地址格式无效")
    try:
        url = httpx.URL(value)
        host = url.host.lower().rstrip(".")
        if (
            url.scheme not in {"http", "https"}
            or not host
            or url.userinfo
            or url.port not in {None, 80 if url.scheme == "http" else 443}
            or "%" in host
            or host == "localhost"
            or host.endswith(
                (".localhost", ".local", ".localdomain", ".internal", ".lan")
            )
        ):
            raise ValueError("disallowed URL")
        sensitive = {
            "token",
            "access_token",
            "auth_token",
            "authorization",
            "api_key",
            "password",
        }
        if any(key.lower() in sensitive for key in url.params.keys()):
            raise ValueError("credential query")
        try:
            literal = ipaddress.ip_address(host)
        except ValueError:
            literal = None
        if literal is not None:
            if not _public_address(str(literal)):
                raise ValueError("non-public IP")
        elif "." not in host or all(part.isdigit() for part in host.split(".")):
            # 127.1、2130706433 等旧式数字写法可能被解析为回环地址，不能当普通域名。
            raise ValueError("ambiguous host")
        return url.copy_with(host=host, fragment=None)
    except (ValueError, httpx.InvalidURL) as exc:
        raise PublicURLValidationError(
            "仅支持不含凭据的公开 HTTP/HTTPS 网页地址"
        ) from exc


async def _resolve_addresses(host: str, port: int) -> list[str]:
    """读取全部 DNS 结果；混合公网和内网的域名也必须拒绝。"""
    rows = await asyncio.get_running_loop().getaddrinfo(
        host, port, type=socket.SOCK_STREAM
    )
    return list(dict.fromkeys(row[4][0] for row in rows))


async def validate_public_target(value: str) -> httpx.URL:
    """核验当前 DNS 均指向公网；MCP 后续自行联网，因此这里不提供 DNS 固定保证。"""
    url = validate_public_url(value)
    try:
        literal = ipaddress.ip_address(url.host)
    except ValueError:
        literal = None
    try:
        addresses = (
            [str(literal)]
            if literal
            else await asyncio.wait_for(
                _resolve_addresses(
                    url.host, url.port or (443 if url.scheme == "https" else 80)
                ),
                timeout=5,
            )
        )
    except (OSError, TimeoutError) as exc:
        raise PublicURLValidationError("公开网页地址暂时无法解析") from exc
    if not addresses or not all(_public_address(address) for address in addresses):
        raise PublicURLValidationError("不允许读取本机、内网或非公网网页")
    return url
