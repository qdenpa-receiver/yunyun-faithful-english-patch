from __future__ import annotations

import os
import re
import tempfile
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from io import IOBase
from pathlib import Path

from UnityPy.enums import ArchiveFlags, ArchiveFlagsOld, CompressionFlags
from UnityPy.helpers import CompressionHelper
from UnityPy.streams import EndianBinaryReader, EndianBinaryWriter

from .errors import PatchError

UNITYFS_CHUNK_SIZE = 0x20000
IO_CHUNK_SIZE = 1024 * 1024
RESOURCE_ASSETS = "resources.assets"


@dataclass(frozen=True)
class UnityFsBlock:
    uncompressed_size: int
    compressed_size: int
    flags: int
    compressed_offset: int


@dataclass(frozen=True)
class UnityFsNode:
    offset: int
    size: int
    flags: int
    path: str


@dataclass(frozen=True)
class UnityFsMetadata:
    signature: str
    version: int
    version_player: str
    version_engine: str
    dataflags: int
    block_info_flags: int
    uses_block_alignment: bool
    blocks_info_at_end: bool
    block_info_need_padding_at_start: bool
    blocks: tuple[UnityFsBlock, ...]
    nodes: tuple[UnityFsNode, ...]


def parse_unityfs_metadata(path: Path) -> UnityFsMetadata:
    with path.open("rb") as handle:
        reader = EndianBinaryReader(handle)
        signature = reader.read_string_to_null()
        if signature != "UnityFS":
            raise PatchError(f"{path.name} is not a UnityFS bundle")

        version = reader.read_u_int()
        version_player = reader.read_string_to_null()
        version_engine = reader.read_string_to_null()
        reader.read_long()
        compressed_info_size = reader.read_u_int()
        uncompressed_info_size = reader.read_u_int()
        dataflags = reader.read_u_int()

        flag_cls = unityfs_archive_flag_type(version_engine)
        dataflag_value = flag_cls(dataflags)

        uses_block_alignment = False
        if version >= 7 or should_align_unityfs(version_engine):
            reader.align_stream(16)
            uses_block_alignment = True

        data_start = reader.Position
        if dataflag_value & flag_cls.BlocksInfoAtTheEnd:
            if dataflag_value & flag_cls.BlockInfoNeedPaddingAtStart:
                reader.align_stream(16)
                data_start = reader.Position
            reader.Position = reader.Length - compressed_info_size
            block_info_bytes = reader.read_bytes(compressed_info_size)
        else:
            block_info_bytes = reader.read_bytes(compressed_info_size)
            if dataflag_value & flag_cls.BlockInfoNeedPaddingAtStart:
                reader.align_stream(16)
            data_start = reader.Position

        if dataflag_value & flag_cls.UsesAssetBundleEncryption:
            raise PatchError("Encrypted UnityFS bundles are not supported by targeted patching")

        block_info = decompress_unityfs_block(
            block_info_bytes,
            uncompressed_info_size,
            dataflags,
            index=0,
        )
        block_reader = EndianBinaryReader(block_info, offset=data_start)
        block_reader.read_bytes(16)

        compressed_offset = data_start
        blocks: list[UnityFsBlock] = []
        for _ in range(block_reader.read_int()):
            block = UnityFsBlock(
                uncompressed_size=block_reader.read_u_int(),
                compressed_size=block_reader.read_u_int(),
                flags=block_reader.read_u_short(),
                compressed_offset=compressed_offset,
            )
            blocks.append(block)
            compressed_offset += block.compressed_size

        nodes = tuple(
            UnityFsNode(
                offset=block_reader.read_long(),
                size=block_reader.read_long(),
                flags=block_reader.read_u_int(),
                path=block_reader.read_string_to_null(),
            )
            for _ in range(block_reader.read_int())
        )

    if not blocks:
        raise PatchError("UnityFS bundle does not contain data blocks")

    block_info_flags = blocks[0].flags
    return UnityFsMetadata(
        signature=signature,
        version=version,
        version_player=version_player,
        version_engine=version_engine,
        dataflags=dataflags,
        block_info_flags=block_info_flags,
        uses_block_alignment=uses_block_alignment,
        blocks_info_at_end=bool(dataflags & 0x80),
        block_info_need_padding_at_start=bool(dataflags & 0x200),
        blocks=tuple(blocks),
        nodes=nodes,
    )


def extract_unityfs_node(
    source: Path,
    metadata: UnityFsMetadata,
    node_path: str,
    output: Path,
) -> None:
    node = find_unityfs_node(metadata, node_path)
    with output.open("wb") as output_handle:
        for chunk in iter_unityfs_node_chunks(source, metadata, node):
            output_handle.write(chunk)

    if output.stat().st_size != node.size:
        raise PatchError(f"Extracted {node_path} has an unexpected size")


def rebuild_unityfs_with_replacement(
    *,
    source: Path,
    metadata: UnityFsMetadata,
    replacement_node_path: str,
    replacement: Path,
    output: Path,
) -> None:
    replacement_size = replacement.stat().st_size
    new_nodes: list[UnityFsNode] = []
    node_streams: list[Iterator[bytes]] = []
    offset = 0
    for node in metadata.nodes:
        size = replacement_size if node.path == replacement_node_path else node.size
        new_nodes.append(
            UnityFsNode(
                offset=offset,
                size=size,
                flags=node.flags,
                path=node.path,
            )
        )
        if node.path == replacement_node_path:
            node_streams.append(iter_file_chunks(replacement))
        else:
            node_streams.append(iter_unityfs_node_chunks(source, metadata, node))
        offset += size

    if not any(node.path == replacement_node_path for node in metadata.nodes):
        raise PatchError(f"UnityFS bundle does not contain {replacement_node_path}")

    fd, compressed_name = tempfile.mkstemp(
        prefix=f".{source.name}.",
        suffix=".blocks.tmp",
        dir=source.parent,
    )
    os.close(fd)
    compressed_path = Path(compressed_name)
    try:
        block_info = compress_unityfs_node_streams(
            node_streams,
            block_info_flag=metadata.block_info_flags,
            compressed_output=compressed_path,
        )
        block_data = build_unityfs_block_data(metadata, tuple(new_nodes), block_info)
        with output.open("wb") as handle:
            write_unityfs_bundle(metadata, block_data, compressed_path, handle)
    finally:
        if compressed_path.exists():
            compressed_path.unlink()


def find_unityfs_node(metadata: UnityFsMetadata, node_path: str) -> UnityFsNode:
    for node in metadata.nodes:
        if node.path == node_path:
            return node
    raise PatchError(f"UnityFS bundle does not contain {node_path}")


def iter_unityfs_node_chunks(
    source: Path,
    metadata: UnityFsMetadata,
    node: UnityFsNode,
) -> Iterator[bytes]:
    node_start = node.offset
    node_end = node.offset + node.size
    uncompressed_offset = 0
    with source.open("rb") as handle:
        for index, block in enumerate(metadata.blocks):
            block_start = uncompressed_offset
            block_end = block_start + block.uncompressed_size
            uncompressed_offset = block_end
            if block_end <= node_start or block_start >= node_end:
                continue

            handle.seek(block.compressed_offset)
            data = decompress_unityfs_block(
                handle.read(block.compressed_size),
                block.uncompressed_size,
                block.flags,
                index=index,
            )
            start = max(node_start, block_start) - block_start
            end = min(node_end, block_end) - block_start
            yield data[start:end]


def iter_file_chunks(path: Path) -> Iterator[bytes]:
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(IO_CHUNK_SIZE)
            if not chunk:
                return
            yield chunk


def compress_unityfs_node_streams(
    node_streams: list[Iterator[bytes]],
    *,
    block_info_flag: int,
    compressed_output: Path,
) -> tuple[tuple[int, int, int], ...]:
    switch_value = block_info_flag & 0x3F
    switch = CompressionFlags(switch_value)
    if switch not in CompressionHelper.COMPRESSION_MAP:
        raise PatchError(f"Unsupported UnityFS compression flag: {switch_value}")
    compress = CompressionHelper.COMPRESSION_MAP[switch]

    block_info: list[tuple[int, int, int]] = []
    pending = bytearray()
    with compressed_output.open("wb") as output:
        for chunks in node_streams:
            for chunk in chunks:
                view = memoryview(chunk)
                while view:
                    take = min(UNITYFS_CHUNK_SIZE - len(pending), len(view))
                    pending.extend(view[:take])
                    view = view[take:]
                    if len(pending) == UNITYFS_CHUNK_SIZE:
                        append_compressed_unityfs_block(
                            bytes(pending),
                            output,
                            block_info,
                            block_info_flag,
                            switch_value,
                            compress,
                        )
                        pending.clear()
        if pending:
            append_compressed_unityfs_block(
                bytes(pending),
                output,
                block_info,
                block_info_flag,
                switch_value,
                compress,
            )
    return tuple(block_info)


def append_compressed_unityfs_block(
    data: bytes,
    output: IOBase,
    block_info: list[tuple[int, int, int]],
    block_info_flag: int,
    switch_value: int,
    compress: Callable[[bytes], bytes],
) -> None:
    compressed = compress(data)
    if len(compressed) > len(data):
        output.write(data)
        block_info.append((len(data), len(data), block_info_flag ^ switch_value))
    else:
        output.write(compressed)
        block_info.append((len(data), len(compressed), block_info_flag))


def build_unityfs_block_data(
    metadata: UnityFsMetadata,
    nodes: tuple[UnityFsNode, ...],
    block_info: tuple[tuple[int, int, int], ...],
) -> bytes:
    writer = EndianBinaryWriter(b"\x00" * 0x10)
    writer.write_int(len(block_info))
    for uncompressed_size, compressed_size, flags in block_info:
        writer.write_u_int(uncompressed_size)
        writer.write_u_int(compressed_size)
        writer.write_u_short(flags)

    if not metadata.dataflags & 0x40:
        raise PatchError("UnityFS targeted patching requires combined directory info")

    writer.write_int(len(nodes))
    for node in nodes:
        writer.write_long(node.offset)
        writer.write_long(node.size)
        writer.write_u_int(node.flags)
        writer.write_string_to_null(node.path)
    return writer.bytes


def write_unityfs_bundle(
    metadata: UnityFsMetadata,
    block_data: bytes,
    compressed_blocks: Path,
    output: IOBase,
) -> None:
    switch_value = metadata.dataflags & 0x3F
    switch = CompressionFlags(switch_value)
    if switch not in CompressionHelper.COMPRESSION_MAP:
        raise PatchError(f"Unsupported UnityFS block-info compression flag: {switch_value}")

    compressed_block_data = CompressionHelper.COMPRESSION_MAP[switch](block_data)
    uncompressed_block_data_size = len(block_data)
    compressed_block_data_size = len(compressed_block_data)

    writer = EndianBinaryWriter(output)
    writer.write_string_to_null(metadata.signature)
    writer.write_u_int(metadata.version)
    writer.write_string_to_null(metadata.version_player)
    writer.write_string_to_null(metadata.version_engine)

    header_pos = writer.Position
    writer.write_long(0)
    writer.write_u_int(compressed_block_data_size)
    writer.write_u_int(uncompressed_block_data_size)
    writer.write_u_int(metadata.dataflags)

    if metadata.uses_block_alignment:
        writer.align_stream(16)

    if metadata.blocks_info_at_end:
        if metadata.block_info_need_padding_at_start:
            writer.align_stream(16)
        write_file_to_unity_writer(compressed_blocks, writer)
        writer.write(compressed_block_data)
    else:
        writer.write(compressed_block_data)
        if metadata.block_info_need_padding_at_start:
            writer.align_stream(16)
        write_file_to_unity_writer(compressed_blocks, writer)

    end_pos = writer.Position
    writer.Position = header_pos
    writer.write_long(end_pos)
    writer.Position = end_pos


def write_file_to_unity_writer(path: Path, writer: EndianBinaryWriter) -> None:
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(IO_CHUNK_SIZE)
            if not chunk:
                return
            writer.write(chunk)


def decompress_unityfs_block(data: bytes, size: int, flags: int, *, index: int) -> bytes:
    if flags & 0x100:
        raise PatchError("Encrypted UnityFS data blocks are not supported by targeted patching")
    compression = CompressionFlags(flags & 0x3F)
    if compression not in CompressionHelper.DECOMPRESSION_MAP:
        raise PatchError(f"Unsupported UnityFS compression flag: {compression.value}")
    return CompressionHelper.DECOMPRESSION_MAP[compression](data, size)


def unityfs_archive_flag_type(version_engine: str) -> type[ArchiveFlags] | type[ArchiveFlagsOld]:
    version = parse_unity_version(version_engine)
    if (
        version < (2020,)
        or (version[0] == 2020 and version < (2020, 3, 34))
        or (version[0] == 2021 and version < (2021, 3, 2))
        or (version[0] == 2022 and version < (2022, 1, 1))
    ):
        return ArchiveFlagsOld
    return ArchiveFlags


def should_align_unityfs(version_engine: str) -> bool:
    version = parse_unity_version(version_engine)
    return version[0] == 2019 and version >= (2019, 4, 15)


def parse_unity_version(version_engine: str) -> tuple[int, ...]:
    match = re.match(r"(\d+)\.(\d+)\.(\d+)\w.+", version_engine or "")
    if not match:
        return (0,)
    return tuple(int(part) for part in match.groups())
