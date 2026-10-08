"""Shared text-UI drawing helpers for menus and building screens."""

from game.constants import COLOR_MENU_DIMMED, COLOR_MENU_NORMAL, COLOR_MENU_SELECTED


def write_str(renderer, y: int, x: int, text: str, color_pair: tuple) -> None:
    if not 0 <= y < renderer.height:
        return
    for i, ch in enumerate(text):
        cx = x + i
        if not 0 <= cx < renderer.width:
            continue
        renderer.set_cell(cx, y, ch, color_pair)


def clear_screen(renderer, color_pair=None) -> None:
    if color_pair is None:
        color_pair = ((0, 0, 0), (0, 0, 0))
    renderer.clear(color_pair)


def list_page(cursor: int, count: int, rows: int) -> range:
    """Indices of the page of a list that contains ``cursor`` (``rows`` per page)."""
    start = (cursor // rows) * rows if rows > 0 else 0
    return range(start, min(count, start + rows))


def render_list(renderer, items: list, cursor: int, top: int, bottom: int) -> None:
    """Draw ``items`` (dicts with "label" and "enabled") between rows top..bottom.

    Long lists are paged so the cursor is always visible; "^"/"v" in the right
    margin mark that more items exist above/below.
    """
    rows = bottom - top + 1
    page = list_page(cursor, len(items), rows)
    for row, idx in enumerate(page, start=top):
        item = items[idx]
        if idx == cursor:
            color = COLOR_MENU_SELECTED
        elif not item["enabled"]:
            color = COLOR_MENU_DIMMED
        else:
            color = COLOR_MENU_NORMAL
        write_str(renderer, row, 0, item["label"], color)

    marker_x = renderer.width - 2
    if page.start > 0:
        write_str(renderer, top, marker_x, "^", COLOR_MENU_DIMMED)
    if page.stop < len(items):
        write_str(renderer, bottom, marker_x, "v", COLOR_MENU_DIMMED)
