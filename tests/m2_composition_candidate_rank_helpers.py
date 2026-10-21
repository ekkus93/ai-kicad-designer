from types import SimpleNamespace

from ai_kicad.m2a import PITCH


def _block(block_id: str, kind: str = "stage", roles: tuple[str, ...] = ()):
    ports = tuple(SimpleNamespace(role=role) for role in roles)
    return SimpleNamespace(id=block_id, kind=kind, ports=ports)


def _plan(blocks, edges=(), precedence=()):
    return SimpleNamespace(blocks=tuple(blocks), edges=tuple(edges), precedence=tuple(precedence))


def _edge(kind: str, source: str, target: str, net: str = "n"):
    return SimpleNamespace(kind=kind, source=source, target=target, net=net)


def _placed(
    block,
    x: int,
    y: int = 0,
    width: int = PITCH,
    height: int = PITCH,
    *,
    positions=None,
    text_positions=None,
    angles=None,
):
    rect = (x, y, x + width, y + height)
    fragment = SimpleNamespace(
        block=block,
        positions=positions or {},
        text_positions=text_positions or {},
        angles=angles or {},
    )
    return SimpleNamespace(
        fragment=fragment,
        content_envelope=rect,
        envelope=rect,
        delta=(x, y),
    )


def _packing(*items):
    return SimpleNamespace(fragments=tuple(items))
