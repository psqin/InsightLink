"""公开网页的有界响应读取：同时限制传输大小和解压后大小。

不能直接使用HTTPX自动解压流，因为一次解码可能在调用方检查长度前展开大量内容。
只支持标准库可限制单次输出的identity、gzip和zlib封装的deflate；其他编码明确拒绝。
"""

import zlib

import httpx


class WebBodyError(ValueError):
    """可安全展示的固定正文读取错误，不附带响应头或外部原文。"""


async def read_bounded_body(response: httpx.Response, maximum: int) -> bytes:
    """逐块读原始字节，用decompress(max_length)在分配输出前限制解压量。

    不调用flush：完整的gzip/deflate帧须在decompress后达到eof，缺尾部或附加数据
    都不能作为完整来源。已缓冲的明文测试适配响应可复用；提前自动解压的压缩
    响应无法再核对原始传输大小，因此拒绝，而非假设它已通过安全检查。
    """
    encoding = response.headers.get("content-encoding", "identity").strip().lower()
    if encoding not in {"", "identity", "gzip", "x-gzip", "deflate"}:
        raise WebBodyError("网站返回了暂不支持的压缩正文编码")
    decoder = None
    if encoding in {"gzip", "x-gzip", "deflate"}:
        if response.is_stream_consumed:
            raise WebBodyError("压缩正文已被提前解码，无法核对原始下载范围")
        decoder = zlib.decompressobj(
            zlib.MAX_WBITS if encoding == "deflate" else zlib.MAX_WBITS + 16
        )
    chunks = (
        response.aiter_bytes(chunk_size=16_384)
        if response.is_stream_consumed
        else response.aiter_raw(chunk_size=16_384)
    )
    body, transferred = bytearray(), 0
    try:
        async for chunk in chunks:
            transferred += len(chunk)
            if transferred > maximum:
                raise WebBodyError("网页超过 2 MiB 下载限制，未将不完整页面作为证据")
            decoded = (
                decoder.decompress(chunk, maximum - len(body) + 1)
                if decoder is not None
                else chunk
            )
            if len(body) + len(decoded) > maximum:
                raise WebBodyError("网页解压后超过 2 MiB 正文限制，已停止读取")
            body.extend(decoded)
            if decoder is not None and decoder.unused_data:
                raise WebBodyError("网页压缩正文含附加数据，无法核实完整范围")
    except zlib.error as exc:
        raise WebBodyError("网页压缩正文损坏，无法可靠读取") from exc
    if decoder is not None and not decoder.eof:
        raise WebBodyError("网页压缩正文不完整，未将残缺内容作为证据")
    return bytes(body)
