"""仅下载导师明确授权的原始 SKILL.md 声明，不提供通用搜索或网页正文读取。"""

import asyncio
import ipaddress
import socket
from collections.abc import Awaitable, Callable, Sequence
from hashlib import sha256
from urllib.parse import urljoin

import httpx

from insight_link_agent.agent.skills.validation import (
    MAX_MARKDOWN_CHARACTERS,
    SkillValidationError,
    validate_skill_url,
)
from insight_link_agent.integrations.public_urls import (
    PublicURLValidationError,
    validate_public_url,
)


class SkillSourceError(Exception):
    """远程技能声明下载失败；不向模型泄露底层网络与认证细节。"""

    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


async def _resolve_addresses(host: str, port: int) -> Sequence[str]:
    """取得全部地址，防止只检查首条 DNS 结果而漏过私网地址。"""
    rows = await asyncio.get_running_loop().getaddrinfo(
        host, port, type=socket.SOCK_STREAM
    )
    return list(dict.fromkeys(row[4][0] for row in rows))


def _public_address(value: str) -> bool:
    """连接地址必须为普通公网 IP，排除隧道、映射与带作用域的 IPv6。"""
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        return False
    return bool(
        address.is_global
        and not address.is_multicast
        and not address.is_unspecified
        and (
            not isinstance(address, ipaddress.IPv6Address)
            or not (
                address.ipv4_mapped
                or address.sixtofour
                or address.teredo
                or address.scope_id
            )
        )
    )


class SkillSourceReader:
    """保留原始换行的短时声明文件读取器，不具备 HTML 提取或网页回退能力。

    技能声明依赖原始 YAML 与 Markdown 换行。这个专用下载入口只接收
    导师明确授权的 SKILL.md；不能作为一般网页读取工具暴露。
    """

    MAX_BYTES = MAX_MARKDOWN_CHARACTERS * 4
    MAX_REDIRECTS = 4
    CONTENT_TYPES = {"text/plain", "text/markdown"}

    def __init__(
        self,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        resolver: Callable[[str, int], Awaitable[Sequence[str]]] | None = None,
        timeout_seconds: float = 20,
    ):
        self._resolver = resolver or _resolve_addresses
        self._timeout = timeout_seconds
        # 环境代理与连接复用都关闭；认证上下文不进入此客户端。
        self._client = httpx.AsyncClient(
            transport=transport,
            trust_env=False,
            follow_redirects=False,
            timeout=10,
            limits=httpx.Limits(max_keepalive_connections=0, max_connections=1),
        )
        # 一次安装至多三次分页，固定一份完整快照，避免页间更新破坏 YAML。
        self._snapshot: tuple[str, dict] | None = None

    async def close(self) -> None:
        """安装完成或取消后释放连接，清除声明文件快照。"""
        self._snapshot = None
        await self._client.aclose()

    @staticmethod
    def _url(value: str) -> httpx.URL:
        """原地址和每次重定向都必须仍是无凭据的公开 SKILL.md。"""
        try:
            validate_skill_url(value)
            return validate_public_url(value)
        except (SkillValidationError, PublicURLValidationError) as exc:
            raise SkillSourceError(
                422, "技能来源必须是不含凭据的公开 SKILL.md 地址"
            ) from exc

    async def _pin(self, url: httpx.URL) -> str:
        """检查全部 DNS 结果后连接固定 IP；Host 与 TLS SNI 仍为原域名。"""
        try:
            literal = ipaddress.ip_address(url.host)
        except ValueError:
            literal = None
        try:
            addresses = (
                [str(literal)]
                if literal
                else await asyncio.wait_for(
                    self._resolver(
                        url.host, url.port or (443 if url.scheme == "https" else 80)
                    ),
                    timeout=5,
                )
            )
        except (OSError, TimeoutError) as exc:
            raise SkillSourceError(503, "技能来源地址暂时无法解析") from exc
        if not addresses or not all(_public_address(address) for address in addresses):
            raise SkillSourceError(422, "不能从本机、内网或非公网地址安装技能")
        return str(addresses[0])

    async def _download(self, url: httpx.URL) -> dict:
        """下载严格有界的声明文本，不跟随到网页、不转发 Cookie 或业务令牌。"""
        for redirect in range(self.MAX_REDIRECTS + 1):
            address = await self._pin(url)
            # 直接创建 Request，避免客户端从前一跳 Set-Cookie 自动拼入 Cookie。
            request = httpx.Request(
                "GET",
                url.copy_with(host=address),
                headers={
                    "Host": url.netloc.decode("ascii"),
                    "Accept": "text/plain,text/markdown",
                    "User-Agent": "InsightLink-SkillSource/1.0",
                    "Accept-Encoding": "identity",
                },
                extensions={
                    "sni_hostname": url.raw_host.decode("ascii"),
                    "timeout": {
                        "connect": 10.0,
                        "read": 10.0,
                        "write": 10.0,
                        "pool": 5.0,
                    },
                },
            )
            response = await self._client.send(request, stream=True)
            try:
                if response.status_code in {301, 302, 303, 307, 308}:
                    location = response.headers.get("location")
                    if not location or redirect == self.MAX_REDIRECTS:
                        raise SkillSourceError(422, "技能来源重定向次数过多或地址无效")
                    url = self._url(urljoin(str(url), location))
                    continue
                if response.status_code != 200:
                    raise SkillSourceError(422, "远程 SKILL.md 暂时无法读取")
                content_type = (
                    response.headers.get("content-type", "")
                    .split(";", 1)[0]
                    .strip()
                    .lower()
                )
                if content_type not in self.CONTENT_TYPES:
                    raise SkillSourceError(
                        422, "远程技能只接受纯文本 SKILL.md，不支持 HTML 或压缩包"
                    )
                if response.headers.get(
                    "content-encoding", "identity"
                ).strip().lower() not in {"", "identity"}:
                    raise SkillSourceError(422, "技能来源须提供未压缩的原始声明文件")
                declared = response.headers.get("content-length")
                if declared is not None:
                    try:
                        size = int(declared)
                    except ValueError as exc:
                        raise SkillSourceError(422, "技能文件大小信息无效") from exc
                    if not 0 <= size <= self.MAX_BYTES:
                        raise SkillSourceError(422, "技能文件超过大小限制")
                raw = bytearray()
                async for chunk in response.aiter_bytes(chunk_size=16_384):
                    raw.extend(chunk)
                    if len(raw) > self.MAX_BYTES:
                        raise SkillSourceError(422, "技能文件超过大小限制")
                try:
                    # 不 strip、不合并空白：frontmatter、缩进与段落必须原样保留。
                    text = bytes(raw).decode(
                        response.encoding or "utf-8", errors="strict"
                    )
                except (UnicodeDecodeError, LookupError) as exc:
                    raise SkillSourceError(
                        422, "SKILL.md 不是有效的纯文本编码"
                    ) from exc
                if (
                    not text.strip()
                    or raw.startswith(b"PK\x03\x04")
                    or text.lstrip("\ufeff \t\r\n")
                    .lower()
                    .startswith(("<!doctype html", "<html", "<?xml"))
                ):
                    raise SkillSourceError(
                        422, "远程技能须为非空 Markdown 声明，不能是 HTML 或压缩包"
                    )
                if len(text) > MAX_MARKDOWN_CHARACTERS:
                    raise SkillSourceError(422, "SKILL.md 超过 24000 字上限")
                return {
                    "url": str(url),
                    "text": text,
                    "content_type": content_type,
                    "source_characters": len(text),
                    "truncated": False,
                    "sha256": sha256(text.encode("utf-8")).hexdigest(),
                }
            finally:
                await response.aclose()
        raise SkillSourceError(422, "技能来源重定向次数过多")

    async def fetch(self, url: str, offset: int = 0, limit: int = 12_000) -> dict:
        """按字符切片同一份原文快照；安装方最多读取三页并复核摘要一致。"""
        parsed = self._url(url)
        if (
            type(offset) is not int
            or not 0 <= offset <= MAX_MARKDOWN_CHARACTERS
            or type(limit) is not int
            or not 1 <= limit <= 12_000
        ):
            raise SkillSourceError(
                422, "技能原文偏移须为非负整数，每次读取数量应在 1–12000 字之间"
            )
        key = str(parsed)
        if self._snapshot is None or self._snapshot[0] != key:
            try:
                async with asyncio.timeout(self._timeout):
                    self._snapshot = key, await self._download(parsed)
            except (httpx.HTTPError, OSError, TimeoutError) as exc:
                raise SkillSourceError(
                    503, "远程技能声明读取暂时不可用，请稍后重试"
                ) from exc
        snapshot = self._snapshot[1]
        end = min(offset + limit, len(snapshot["text"]))
        return {
            **snapshot,
            "ok": True,
            "text": snapshot["text"][offset:end],
            "next_offset": end if end < len(snapshot["text"]) else None,
        }
