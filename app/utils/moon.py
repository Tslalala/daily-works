"""Moon-phase geometry for the target badge.

The badge is a circle that is always fully "lit" (its gradient). On top of it,
a wireframe-globe overlay covers the unfinished part and retreats as progress
grows — like cloud clearing over the moon. The terminator is a half-ellipse
(real moon phases); the whole geometry is rotated 135deg in the template so
the lit side is exposed from the bottom-left (the 45deg line):

    0%   overlay covers the whole circle
    33%  overlay = a cap on the top-right, lit crescent at the bottom-left
    50%  straight 45deg terminator
    100% no overlay, full gradient
"""


def moon_shadow_path(progress, r=20):
    """SVG path for the overlay (shadow) region, standard orientation.

    Standard orientation: lit side = right, so the shadow sits on the left.
    The template rotates it 135deg around the centre, which points the lit
    side to the bottom-left. Returns "" when progress is 100%.
    """
    p = max(0.0, min(100.0, float(progress or 0))) / 100.0
    if p >= 1.0:
        return ""
    c = r
    if p <= 0.0:
        # Full coverage: use the bounding box as the clip (a no-op, since the
        # overlay content is already the r circle). A two-arc full-circle path
        # does not render reliably in Chromium clip-path rasterization.
        return f"M0,0 H{2 * c} V{2 * c} H0 Z"
    if p <= 0.5:
        # Shadow = left half + bulge into the lit side.
        # a runs c (p=0, full circle) -> 0 (p=0.5, straight terminator).
        a = c * (1 - 2 * p)
        sweep = "1"
    else:
        # Shadow = a crescent on the left.
        # a runs 0 (p=0.5) -> c (p=1, nothing left).
        a = c * (2 * p - 1)
        sweep = "0"
    return f"M{c},0 A{c},{c} 0 0 0 {c},{2 * c} A{a:.2f},{c} 0 0 {sweep} {c},0 Z"
