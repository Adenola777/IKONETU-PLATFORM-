"""The Lucide 0.544.0 icons and the IkonetU lockup, drawn inline so they cost no request.

Converted on 17 October 2026 from apps/web/components/site/icons.tsx and logo.tsx,
which tools/gen_next.py generated from the design boards. The markup is the
markup React rendered for them. house, video, file-check, compass, ellipsis-vertical, send,
log-out and info were added on 26 October 2026 from lucide-static 0.544.0 for the app frame,
and rocket and briefcase the same day for the choice of founder or investor.
"""

from markupsafe import Markup

SHAPES = {
    "activity": "<path d=\"M22 12h-2.48a2 2 0 0 0-1.93 1.46l-2.35 8.36a.25.25 0 0 1-.48 0L9.24 2.18a.25.25 0 0 0-.48 0l-2.35 8.36A2 2 0 0 1 4.49 12H2\"></path>",
    "arrow-left": "<path d=\"m12 19-7-7 7-7\"></path><path d=\"M19 12H5\"></path>",
    "arrow-right": "<path d=\"M5 12h14\"></path><path d=\"m12 5 7 7-7 7\"></path>",
    "briefcase": "<path d=\"M16 20V4a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16\"></path><rect width=\"20\" height=\"14\" x=\"2\" y=\"6\" rx=\"2\"></rect>",
    "calendar-check": "<path d=\"M8 2v4\"></path><path d=\"M16 2v4\"></path><rect width=\"18\" height=\"18\" x=\"3\" y=\"4\" rx=\"2\"></rect><path d=\"M3 10h18\"></path><path d=\"m9 16 2 2 4-4\"></path>",
    "captions": "<rect width=\"18\" height=\"14\" x=\"3\" y=\"5\" rx=\"2\" ry=\"2\"></rect><path d=\"M7 15h4M15 15h2M7 11h2M13 11h4\"></path>",
    "check": "<path d=\"M20 6 9 17l-5-5\"></path>",
    "chevron-down": "<path d=\"m6 9 6 6 6-6\"></path>",
    "chevron-left": "<path d=\"m15 18-6-6 6-6\"></path>",
    "chevron-right": "<path d=\"m9 18 6-6-6-6\"></path>",
    "circle-alert": "<circle cx=\"12\" cy=\"12\" r=\"10\"></circle><line x1=\"12\" x2=\"12\" y1=\"8\" y2=\"12\"></line><line x1=\"12\" x2=\"12.01\" y1=\"16\" y2=\"16\"></line>",
    "circle-check": "<circle cx=\"12\" cy=\"12\" r=\"10\"></circle><path d=\"m9 12 2 2 4-4\"></path>",
    "circle-dashed": "<path d=\"M10.1 2.182a10 10 0 0 1 3.8 0\"></path><path d=\"M13.9 21.818a10 10 0 0 1-3.8 0\"></path><path d=\"M17.609 3.721a10 10 0 0 1 2.69 2.7\"></path><path d=\"M2.182 13.9a10 10 0 0 1 0-3.8\"></path><path d=\"M20.279 17.609a10 10 0 0 1-2.7 2.69\"></path><path d=\"M21.818 10.1a10 10 0 0 1 0 3.8\"></path><path d=\"M3.721 6.391a10 10 0 0 1 2.7-2.69\"></path><path d=\"M6.391 20.279a10 10 0 0 1-2.69-2.7\"></path>",
    "circle-play": "<path d=\"M9 9.003a1 1 0 0 1 1.517-.859l4.997 2.997a1 1 0 0 1 0 1.718l-4.997 2.997A1 1 0 0 1 9 14.996z\"></path><circle cx=\"12\" cy=\"12\" r=\"10\"></circle>",
    "clock": "<path d=\"M12 6v6l4 2\"></path><circle cx=\"12\" cy=\"12\" r=\"10\"></circle>",
    "compass": "<path d=\"m16.24 7.76-1.804 5.411a2 2 0 0 1-1.265 1.265L7.76 16.24l1.804-5.411a2 2 0 0 1 1.265-1.265z\"></path><circle cx=\"12\" cy=\"12\" r=\"10\"></circle>",
    "ellipsis-vertical": "<circle cx=\"12\" cy=\"12\" r=\"1\"></circle><circle cx=\"12\" cy=\"5\" r=\"1\"></circle><circle cx=\"12\" cy=\"19\" r=\"1\"></circle>",
    "eye": "<path d=\"M2.062 12.348a1 1 0 0 1 0-.696 10.75 10.75 0 0 1 19.876 0 1 1 0 0 1 0 .696 10.75 10.75 0 0 1-19.876 0\"></path><circle cx=\"12\" cy=\"12\" r=\"3\"></circle>",
    "eye-off": "<path d=\"M10.733 5.076a10.744 10.744 0 0 1 11.205 6.575 1 1 0 0 1 0 .696 10.747 10.747 0 0 1-1.444 2.49\"></path><path d=\"M14.084 14.158a3 3 0 0 1-4.242-4.242\"></path><path d=\"M17.479 17.499a10.75 10.75 0 0 1-15.417-5.151 1 1 0 0 1 0-.696 10.75 10.75 0 0 1 4.446-5.143\"></path><path d=\"m2 2 20 20\"></path>",
    "file-check": "<path d=\"M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z\"></path><path d=\"M14 2v4a2 2 0 0 0 2 2h4\"></path><path d=\"m9 15 2 2 4-4\"></path>",
    "file-text": "<path d=\"M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z\"></path><path d=\"M14 2v4a2 2 0 0 0 2 2h4\"></path><path d=\"M10 9H8\"></path><path d=\"M16 13H8\"></path><path d=\"M16 17H8\"></path>",
    "flag": "<path d=\"M4 22V4a1 1 0 0 1 .4-.8A6 6 0 0 1 8 2c3 0 5 2 7.333 2q2 0 3.067-.8A1 1 0 0 1 20 4v10a1 1 0 0 1-.4.8A6 6 0 0 1 16 16c-3 0-5-2-8-2a6 6 0 0 0-4 1.528\"></path>",
    "funnel": "<path d=\"M10 20a1 1 0 0 0 .553.895l2 1A1 1 0 0 0 14 21v-7a2 2 0 0 1 .517-1.341L21.74 4.67A1 1 0 0 0 21 3H3a1 1 0 0 0-.742 1.67l7.225 7.989A2 2 0 0 1 10 14z\"></path>",
    "handshake": "<path d=\"m11 17 2 2a1 1 0 1 0 3-3\"></path><path d=\"m14 14 2.5 2.5a1 1 0 1 0 3-3l-3.88-3.88a3 3 0 0 0-4.24 0l-.88.88a1 1 0 1 1-3-3l2.81-2.81a5.79 5.79 0 0 1 7.06-.87l.47.28a2 2 0 0 0 1.42.25L21 4\"></path><path d=\"m21 3 1 11h-2\"></path><path d=\"M3 3 2 14l6.5 6.5a1 1 0 1 0 3-3\"></path><path d=\"M3 4h8\"></path>",
    "house": "<path d=\"M15 21v-8a1 1 0 0 0-1-1h-4a1 1 0 0 0-1 1v8\"></path><path d=\"M3 10a2 2 0 0 1 .709-1.528l7-6a2 2 0 0 1 2.582 0l7 6A2 2 0 0 1 21 10v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z\"></path>",
    "id-card": "<path d=\"M16 10h2\"></path><path d=\"M16 14h2\"></path><path d=\"M6.17 15a3 3 0 0 1 5.66 0\"></path><circle cx=\"9\" cy=\"11\" r=\"2\"></circle><rect x=\"2\" y=\"5\" width=\"20\" height=\"14\" rx=\"2\"></rect>",
    "info": "<circle cx=\"12\" cy=\"12\" r=\"10\"></circle><path d=\"M12 16v-4\"></path><path d=\"M12 8h.01\"></path>",
    "link": "<path d=\"M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71\"></path><path d=\"M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71\"></path>",
    "list-checks": "<path d=\"M13 5h8\"></path><path d=\"M13 12h8\"></path><path d=\"M13 19h8\"></path><path d=\"m3 17 2 2 4-4\"></path><path d=\"m3 7 2 2 4-4\"></path>",
    "lock": "<rect width=\"18\" height=\"11\" x=\"3\" y=\"11\" rx=\"2\" ry=\"2\"></rect><path d=\"M7 11V7a5 5 0 0 1 10 0v4\"></path>",
    "log-out": "<path d=\"m16 17 5-5-5-5\"></path><path d=\"M21 12H9\"></path><path d=\"M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4\"></path>",
    "menu": "<path d=\"M4 5h16\"></path><path d=\"M4 12h16\"></path><path d=\"M4 19h16\"></path>",
    "message-square": "<path d=\"M22 17a2 2 0 0 1-2 2H6.828a2 2 0 0 0-1.414.586l-2.202 2.202A.71.71 0 0 1 2 21.286V5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2z\"></path>",
    "pause": "<rect x=\"14\" y=\"3\" width=\"5\" height=\"18\" rx=\"1\"></rect><rect x=\"5\" y=\"3\" width=\"5\" height=\"18\" rx=\"1\"></rect>",
    "play": "<path d=\"M5 5a2 2 0 0 1 3.008-1.728l11.997 6.998a2 2 0 0 1 .003 3.458l-12 7A2 2 0 0 1 5 19z\"></path>",
    "plus": "<path d=\"M5 12h14\"></path><path d=\"M12 5v14\"></path>",
    "rocket": "<path d=\"M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z\"></path><path d=\"m12 15-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 0 1-4 2z\"></path><path d=\"M9 12H4s.55-3.03 2-4c1.62-1.08 5 0 5 0\"></path><path d=\"M12 15v5s3.03-.55 4-2c1.08-1.62 0-5 0-5\"></path>",
    "rotate-ccw": "<path d=\"M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8\"></path><path d=\"M3 3v5h5\"></path>",
    "search": "<path d=\"m21 21-4.34-4.34\"></path><circle cx=\"11\" cy=\"11\" r=\"8\"></circle>",
    "send": "<path d=\"M14.536 21.686a.5.5 0 0 0 .937-.024l6.5-19a.496.496 0 0 0-.635-.635l-19 6.5a.5.5 0 0 0-.024.937l7.93 3.18a2 2 0 0 1 1.112 1.11z\"></path><path d=\"m21.854 2.147-10.94 10.939\"></path>",
    "shield-check": "<path d=\"M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z\"></path><path d=\"m9 12 2 2 4-4\"></path>",
    "square-pen": "<path d=\"M12 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7\"></path><path d=\"M18.375 2.625a1 1 0 0 1 3 3l-9.013 9.014a2 2 0 0 1-.853.505l-2.873.84a.5.5 0 0 1-.62-.62l.84-2.873a2 2 0 0 1 .506-.852z\"></path>",
    "upload": "<path d=\"M12 3v12\"></path><path d=\"m17 8-5-5-5 5\"></path><path d=\"M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4\"></path>",
    "user-round": "<circle cx=\"12\" cy=\"8\" r=\"5\"></circle><path d=\"M20 21a8 8 0 0 0-16 0\"></path>",
    "video": "<path d=\"m16 13 5.223 3.482a.5.5 0 0 0 .777-.416V7.87a.5.5 0 0 0-.752-.432L16 10.5\"></path><rect x=\"2\" y=\"6\" width=\"14\" height=\"12\" rx=\"2\"></rect>",
    "volume-x": "<path d=\"M11 4.702a.705.705 0 0 0-1.203-.498L6.413 7.587A1.4 1.4 0 0 1 5.416 8H3a1 1 0 0 0-1 1v6a1 1 0 0 0 1 1h2.416a1.4 1.4 0 0 1 .997.413l3.383 3.384A.705.705 0 0 0 11 19.298z\"></path><line x1=\"22\" x2=\"16\" y1=\"9\" y2=\"15\"></line><line x1=\"16\" x2=\"22\" y1=\"9\" y2=\"15\"></line>",
    "x": "<path d=\"M18 6 6 18\"></path><path d=\"m6 6 12 12\"></path>",
}

_LOGO = {
    "default": "<g transform=\"translate(-7.286 -2.429) scale(0.8095)\"><path d=\"M9 4.5 Q9 3 10.5 3 L37.5 3 Q39 3 39 4.5 L39 10.5 Q39 12 37.5 12 L34.5 12 Q33 12 33 13.5 L33 28.5 Q33 30 31.5 30 L28.5 30 Q27 30 27 28.5 L27 13.5 Q27 12 25.5 12 L10.5 12 Q9 12 9 10.5 Z\" fill=\"#123C7A\"></path><path d=\"M39 43.5 Q39 45 37.5 45 L10.5 45 Q9 45 9 43.5 L9 37.5 Q9 36 10.5 36 L13.5 36 Q15 36 15 34.5 L15 19.5 Q15 18 16.5 18 L19.5 18 Q21 18 21 19.5 L21 34.5 Q21 36 22.5 36 L37.5 36 Q39 36 39 37.5 Z\" fill=\"#F26B1D\"></path></g><g transform=\"translate(33.651 8.053) scale(0.02402)\"><path d=\"M72 745V0H208V745Z M426.0 745V0H562.0V388L525.0 375L842.0 0H1013.0L716.0 352L724.0 256L1022.0 745H862.0L662.0 417L562.0 536V745Z M1527.0 757Q1445.0 757 1374.0 728.0Q1303.0 699 1250.0 647.0Q1197.0 595 1167.5 524.5Q1138.0 454 1138.0 372Q1138.0 289 1167.0 219.0Q1196.0 149 1249.0 97.0Q1302.0 45 1373.0 16.5Q1444.0 -12 1527.0 -12Q1610.0 -12 1681.0 17.0Q1752.0 46 1805.0 97.5Q1858.0 149 1887.5 219.0Q1917.0 289 1917.0 372Q1917.0 454 1887.0 524.5Q1857.0 595 1804.0 647.0Q1751.0 699 1680.5 728.0Q1610.0 757 1527.0 757ZM1527.0 633Q1582.0 633 1628.0 613.5Q1674.0 594 1708.5 559.0Q1743.0 524 1761.5 476.0Q1780.0 428 1780.0 372Q1780.0 316 1761.5 268.5Q1743.0 221 1708.5 185.5Q1674.0 150 1628.0 131.0Q1582.0 112 1527.0 112Q1473.0 112 1427.0 131.0Q1381.0 150 1346.5 185.5Q1312.0 221 1293.0 268.5Q1274.0 316 1274.0 372Q1274.0 428 1293.0 476.0Q1312.0 524 1346.5 559.0Q1381.0 594 1427.0 613.5Q1473.0 633 1527.0 633Z M2113.0 745V0H2219.0L2629.0 552L2574.0 563V0H2710.0V745H2603.0L2199.0 189L2249.0 178V745Z M2929.0 745V0H3424.0V120H3065.0V311H3404.0V431H3065.0V625H3424.0V745Z M3725.0 745V120H3532.0V0H4052.0V120H3862.0V745Z M4487.0 757Q4401.0 757 4334.5 721.0Q4268.0 685 4230.0 622.0Q4192.0 559 4192.0 479V0H4328.0V472Q4328.0 518 4348.5 555.0Q4369.0 592 4405.0 612.5Q4441.0 633 4487.0 633Q4534.0 633 4569.5 612.5Q4605.0 592 4625.5 555.0Q4646.0 518 4646.0 472V0H4782.0V479Q4782.0 559 4744.0 622.0Q4706.0 685 4639.5 721.0Q4573.0 757 4487.0 757Z\" fill=\"#123C7A\"></path></g>",
    "navy": "<g transform=\"translate(-7.286 -2.429) scale(0.8095)\"><path d=\"M9 4.5 Q9 3 10.5 3 L37.5 3 Q39 3 39 4.5 L39 10.5 Q39 12 37.5 12 L34.5 12 Q33 12 33 13.5 L33 28.5 Q33 30 31.5 30 L28.5 30 Q27 30 27 28.5 L27 13.5 Q27 12 25.5 12 L10.5 12 Q9 12 9 10.5 Z\" fill=\"#FFFFFF\"></path><path d=\"M39 43.5 Q39 45 37.5 45 L10.5 45 Q9 45 9 43.5 L9 37.5 Q9 36 10.5 36 L13.5 36 Q15 36 15 34.5 L15 19.5 Q15 18 16.5 18 L19.5 18 Q21 18 21 19.5 L21 34.5 Q21 36 22.5 36 L37.5 36 Q39 36 39 37.5 Z\" fill=\"#F26B1D\"></path></g><g transform=\"translate(33.651 8.053) scale(0.02402)\"><path d=\"M72 745V0H208V745Z M426.0 745V0H562.0V388L525.0 375L842.0 0H1013.0L716.0 352L724.0 256L1022.0 745H862.0L662.0 417L562.0 536V745Z M1527.0 757Q1445.0 757 1374.0 728.0Q1303.0 699 1250.0 647.0Q1197.0 595 1167.5 524.5Q1138.0 454 1138.0 372Q1138.0 289 1167.0 219.0Q1196.0 149 1249.0 97.0Q1302.0 45 1373.0 16.5Q1444.0 -12 1527.0 -12Q1610.0 -12 1681.0 17.0Q1752.0 46 1805.0 97.5Q1858.0 149 1887.5 219.0Q1917.0 289 1917.0 372Q1917.0 454 1887.0 524.5Q1857.0 595 1804.0 647.0Q1751.0 699 1680.5 728.0Q1610.0 757 1527.0 757ZM1527.0 633Q1582.0 633 1628.0 613.5Q1674.0 594 1708.5 559.0Q1743.0 524 1761.5 476.0Q1780.0 428 1780.0 372Q1780.0 316 1761.5 268.5Q1743.0 221 1708.5 185.5Q1674.0 150 1628.0 131.0Q1582.0 112 1527.0 112Q1473.0 112 1427.0 131.0Q1381.0 150 1346.5 185.5Q1312.0 221 1293.0 268.5Q1274.0 316 1274.0 372Q1274.0 428 1293.0 476.0Q1312.0 524 1346.5 559.0Q1381.0 594 1427.0 613.5Q1473.0 633 1527.0 633Z M2113.0 745V0H2219.0L2629.0 552L2574.0 563V0H2710.0V745H2603.0L2199.0 189L2249.0 178V745Z M2929.0 745V0H3424.0V120H3065.0V311H3404.0V431H3065.0V625H3424.0V745Z M3725.0 745V120H3532.0V0H4052.0V120H3862.0V745Z M4487.0 757Q4401.0 757 4334.5 721.0Q4268.0 685 4230.0 622.0Q4192.0 559 4192.0 479V0H4328.0V472Q4328.0 518 4348.5 555.0Q4369.0 592 4405.0 612.5Q4441.0 633 4487.0 633Q4534.0 633 4569.5 612.5Q4605.0 592 4625.5 555.0Q4646.0 518 4646.0 472V0H4782.0V479Q4782.0 559 4744.0 622.0Q4706.0 685 4639.5 721.0Q4573.0 757 4487.0 757Z\" fill=\"#FFFFFF\"></path></g>",
}


def icon(name: str, size: int = 20, fill: bool = False) -> Markup:
    return Markup(
        f'<svg class="lucide lucide-{name}" aria-hidden="true" width="{size}" height="{size}" viewBox="0 0 24 24" '
        f'fill="{"currentColor" if fill else "none"}" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
        f'stroke-linejoin="round" style="flex:none">{SHAPES[name]}</svg>'
    )


def logo(variant: str = "default", height: int = 34) -> Markup:
    """The default colours sit on white, and the navy colours sit on the navy footer."""
    width = f"{height * 4.36765:.1f}"
    return Markup(
        f'<svg aria-hidden="true" width="{width}" height="{height}" viewBox="0 0 148.51 34.00" '
        f'style="display:block;flex:none">{_LOGO[variant]}</svg>'
    )


def mark(height: int = 28) -> Markup:
    """The IkonetU mark without the wordmark, for the narrow header of the app on a phone."""
    group = _LOGO["default"].split("</g>")[0] + "</g>"
    return Markup(
        f'<svg aria-hidden="true" width="{height * 24.28 / 34:.1f}" height="{height}" viewBox="0 0 24.28 34" '
        f'style="display:block;flex:none">{group}</svg>'
    )
