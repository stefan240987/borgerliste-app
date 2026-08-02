from __future__ import annotations
import html
import json
import streamlit as st
import streamlit.components.v1 as components
from config import (
    FILTER_ACTIVE_COLORS, PRIMARY_COLOR, PRIMARY_TEXT, SIDEBAR_AUTO_COLLAPSE_SECONDS,
    STATUSES, STATUS_PILL_CLASS, THEME_PALETTES,
)
from i18n import filter_label, status_label, t


def status_pill_html(status: str, short: bool = True) -> str:
    pill_class = STATUS_PILL_CLASS.get(status, "status-pill--neutral")
    label = status_label(status, short=short)
    return f'<span class="status-pill {pill_class}">{html.escape(label)}</span>'


def _admin_badge(label: str, variant: str) -> str:
    return f'<span class="admin-badge admin-badge--{html.escape(variant)}">{html.escape(label)}</span>'


def admin_role_badge_html(role: str) -> str:
    from auth import role_label

    variant = "role-admin" if role == "admin" else "role-user"
    return _admin_badge(role_label(role), variant)


def admin_license_badge_html(user: dict) -> str:
    from licensing import license_status_key, trial_days_remaining

    role = str(user.get("role", "user"))
    if role == "admin":
        return _admin_badge(t("license_status_admin"), "license-admin")

    key = license_status_key(user)
    if key == "license_status_paid":
        return _admin_badge(t(key), "license-paid")
    if key == "license_status_expired":
        return _admin_badge(t(key), "license-expired")

    days = trial_days_remaining(user)
    if days is not None:
        return _admin_badge(t("sidebar_license_trial", days=days), "license-trial")
    return _admin_badge(t(key), "license-trial")


def admin_municipality_badges_html(municipalities: list[str] | None = None) -> str:
    if not municipalities:
        return f'<span class="admin-municipality-none">{html.escape(t("admin_municipalities_none"))}</span>'
    chips = "".join(
        f'<span class="admin-badge admin-municipality-badge">{html.escape(name)}</span>'
        for name in municipalities
    )
    return f'<span class="admin-municipality-group">{chips}</span>'


def citizen_field_html(label: str, value: object, *, emphasized: bool = False) -> str:
    safe_label = html.escape(label)
    safe_value = html.escape(str(value))
    emphasis_class = " citizen-field-value--emphasis" if emphasized else ""
    return (
        f'<div class="citizen-field">'
        f'<span class="citizen-field-label">{safe_label}</span>'
        f'<span class="citizen-field-value{emphasis_class}">{safe_value}</span>'
        f"</div>"
    )


def _status_pill_css(scheme: str) -> str:
    if scheme == "dark":
        return """
.status-pill {
    display: inline-block;
    padding: 0.25rem 0.65rem;
    border-radius: 999px;
    font-size: 0.75rem;
    font-weight: 700;
    line-height: 1.3;
    white-space: nowrap;
    border: 1px solid transparent;
}
.status-pill--neutral {
    background: #334155 !important;
    color: #E2E8F0 !important;
    border-color: #64748B !important;
}
.status-pill--accepted {
    background: #14532D !important;
    color: #BBF7D0 !important;
    border-color: #22C55E !important;
}
.status-pill--declined {
    background: #7F1D1D !important;
    color: #FECACA !important;
    border-color: #EF4444 !important;
}
.status-pill--call-again {
    background: #78350F !important;
    color: #FDE68A !important;
    border-color: #F59E0B !important;
}
.status-pill--all {
    background: #312E81 !important;
    color: #E0E7FF !important;
    border-color: #6366F1 !important;
}
"""
    return """
.status-pill {
    display: inline-block;
    padding: 0.25rem 0.65rem;
    border-radius: 999px;
    font-size: 0.75rem;
    font-weight: 700;
    line-height: 1.3;
    white-space: nowrap;
    border: 1px solid transparent;
}
.status-pill--neutral {
    background: #F1F5F9 !important;
    color: #475569 !important;
    border-color: #CBD5E1 !important;
}
.status-pill--accepted {
    background: #DCFCE7 !important;
    color: #15803D !important;
    border-color: #86EFAC !important;
}
.status-pill--declined {
    background: #FEE2E2 !important;
    color: #B91C1C !important;
    border-color: #FCA5A5 !important;
}
.status-pill--call-again {
    background: #FEF3C7 !important;
    color: #B45309 !important;
    border-color: #FCD34D !important;
}
.status-pill--all {
    background: #EEF2FF !important;
    color: #3730A3 !important;
    border-color: #C7D2FE !important;
}
"""


def _btn_secondary_selector(scope: str = "") -> str:
    prefix = f"{scope} " if scope else ""
    return (
        f"{prefix}.stButton > button[kind=\"secondary\"], "
        f"{prefix}.stButton button[data-testid=\"stBaseButton-secondary\"], "
        f"{prefix}.stButton button[kind=\"secondary\"]"
    )


def _btn_primary_selector(scope: str = "") -> str:
    prefix = f"{scope} " if scope else ""
    return (
        f"{prefix}.stButton > button[kind=\"primary\"], "
        f"{prefix}.stButton button[data-testid=\"stBaseButton-primary\"], "
        f"{prefix}.stButton button[kind=\"primary\"]"
    )


def _btn_any_selector(scope: str = "") -> str:
    prefix = f"{scope} " if scope else ""
    return (
        f"{prefix}.stButton > button, "
        f"{prefix}.stButton button[data-testid=\"stBaseButton-secondary\"], "
        f"{prefix}.stButton button[data-testid=\"stBaseButton-primary\"], "
        f"{prefix}.stButton button[kind=\"secondary\"], "
        f"{prefix}.stButton button[kind=\"primary\"]"
    )


def _overview_columns_selector() -> str:
    return (
        '[data-testid="stElementContainer"]:has(#kpi-overview-anchor) + '
        '[data-testid="stLayoutWrapper"] [data-testid="stColumn"]'
    )


def _overview_filter_button_selector(suffix: str = "") -> str:
    return _btn_any_selector(f"{_overview_columns_selector()}{suffix}")


def _kpi_filter_active_color_rules(theme_prefix: str) -> str:
    rules: list[str] = []
    for index, (_filter_key, color) in enumerate(FILTER_ACTIVE_COLORS.items(), start=1):
        column = f"{_overview_columns_selector()}:nth-child({index})"
        primary_btns = _btn_primary_selector(column)
        rules.append(
            f"""
{theme_prefix} {primary_btns} {{
    background-color: {color} !important;
    color: #FFFFFF !important;
    border: 1px solid {color} !important;
    -webkit-text-fill-color: #FFFFFF !important;
}}
{theme_prefix} {column}:has(button[kind="primary"]) div[data-testid="stVerticalBlockBorderWrapper"],
{theme_prefix} {column}:has(button[data-testid="stBaseButton-primary"]) div[data-testid="stVerticalBlockBorderWrapper"] {{
    border: 2px solid {color} !important;
    box-shadow: 0 0 0 3px {color}33 !important;
}}
"""
        )
    return "\n".join(rules)


def _light_theme_field_css(scope: str = "") -> str:
    sp = f"{scope} " if scope else ""
    return f"""
{sp}div[data-testid="stTextInput"] input,
{sp}div[data-baseweb="input"] input,
{sp}div[data-testid="stSelectbox"] [data-baseweb="select"],
{sp}div[data-testid="stSelectbox"] div[data-baseweb="select"],
{sp}div[data-testid="stMultiSelect"] div[data-baseweb="select"],
{sp}div[data-baseweb="select"] > div,
{sp}div[data-baseweb="select"] {{
    background-color: #FFFFFF !important;
    color: #111827 !important;
    -webkit-text-fill-color: #111827 !important;
    border: 1px solid #9CA3AF !important;
    caret-color: #111827 !important;
}}

{sp}div[data-testid="stSelectbox"] [data-baseweb="select"] *,
{sp}div[data-baseweb="select"] div,
{sp}div[data-baseweb="select"] span {{
    color: #111827 !important;
    -webkit-text-fill-color: #111827 !important;
}}

{sp}div[data-baseweb="select"] svg {{
    fill: #111827 !important;
}}

{sp}div[data-testid="stTextInput"] input::placeholder,
{sp}div[data-baseweb="input"] input::placeholder {{
    color: #6B7280 !important;
    -webkit-text-fill-color: #6B7280 !important;
    opacity: 1 !important;
}}
"""


def _light_theme_overrides_css() -> str:
    col_sel = _overview_columns_selector()
    overview_buttons = _overview_filter_button_selector()
    overview_secondary = _btn_secondary_selector(f".light-theme {col_sel}")
    active_rules = _kpi_filter_active_color_rules(".light-theme")
    return f"""
.light-theme {{
    color-scheme: light !important;
}}

{overview_secondary} {{
    background-color: #FFFFFF !important;
    color: #1F2937 !important;
    border: 1px solid #D1D5DB !important;
    -webkit-text-fill-color: #1F2937 !important;
}}

.light-theme {overview_buttons} {{
    height: 42px !important;
    min-height: 42px !important;
    max-height: 42px !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    font-size: 0.82rem !important;
    font-weight: 600 !important;
    line-height: 1.1 !important;
    box-shadow: none !important;
}}

{_light_theme_field_css(".light-theme")}

{active_rules}
"""


def _light_theme_tooltip_css(scope: str = "") -> str:
    sp = f"{scope} " if scope else ""
    return f"""
{sp}div[data-baseweb="tooltip"] > div,
{sp}div[data-baseweb="popover"]:has([data-testid="stTooltipContent"]) > div,
{sp}div[data-baseweb="popover"]:has(.stTooltipContent) > div,
{sp}div[role="tooltip"],
{sp}div[role="tooltip"] > div {{
    background-color: #FFFFFF !important;
    color: #111827 !important;
    border: 1px solid #D1D5DB !important;
    box-shadow: 0 4px 12px rgba(15, 23, 42, 0.12) !important;
}}

{sp}div[data-baseweb="tooltip"],
{sp}div[role="tooltip"] {{
    color: #111827 !important;
}}

{sp}[data-testid="stTooltipContent"],
{sp}.stTooltipContent,
{sp}[data-testid="stTooltipContent"] *,
{sp}.stTooltipContent *,
{sp}div[data-baseweb="tooltip"] *,
{sp}div[role="tooltip"] * {{
    color: #111827 !important;
    -webkit-text-fill-color: #111827 !important;
}}
"""


def _dark_theme_field_css(scope: str = "") -> str:
    sp = f"{scope} " if scope else ""
    return f"""
{sp}div[data-testid="stTextInput"] input,
{sp}div[data-baseweb="input"] input,
{sp}div[data-testid="stSelectbox"] [data-baseweb="select"],
{sp}div[data-testid="stSelectbox"] div[data-baseweb="select"],
{sp}div[data-testid="stMultiSelect"] div[data-baseweb="select"],
{sp}div[data-baseweb="select"] > div,
{sp}div[data-baseweb="select"] {{
    background-color: #1E293B !important;
    color: #F8FAFC !important;
    -webkit-text-fill-color: #F8FAFC !important;
    border: 1px solid #334155 !important;
    caret-color: #F8FAFC !important;
}}

{sp}div[data-testid="stSelectbox"] [data-baseweb="select"] *,
{sp}div[data-baseweb="select"] div,
{sp}div[data-baseweb="select"] span {{
    color: #F8FAFC !important;
    -webkit-text-fill-color: #F8FAFC !important;
}}

{sp}div[data-baseweb="select"] svg {{
    fill: #F8FAFC !important;
}}

{sp}div[data-testid="stTextInput"] input::placeholder,
{sp}div[data-baseweb="input"] input::placeholder {{
    color: #94A3B8 !important;
    -webkit-text-fill-color: #94A3B8 !important;
    opacity: 1 !important;
}}
"""


def _toast_shell_css(
    scope: str,
    *,
    bg: str,
    text: str,
    border: str,
    shadow: str,
    button: str,
) -> str:
    sp = f"{scope} " if scope else ""
    return f"""
{sp}[data-testid="stToast"],
{sp}.stToast {{
    background-color: {bg} !important;
    color: {text} !important;
    border: 1px solid {border} !important;
    box-shadow: {shadow} !important;
    border-radius: 0.65rem !important;
    overflow: hidden !important;
}}

{sp}[data-testid="stToast"] > div,
{sp}[data-testid="stToast"] div,
{sp}.stToast > div,
{sp}.stToast div {{
    background: transparent !important;
    background-color: transparent !important;
    border: none !important;
    box-shadow: none !important;
    outline: none !important;
}}

{sp}[data-testid="stToast"] *,
{sp}.stToast * {{
    color: {text} !important;
    -webkit-text-fill-color: {text} !important;
}}

{sp}[data-testid="stToast"] button,
{sp}.stToast button {{
    color: {button} !important;
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
}}
"""


def _light_theme_toast_css(scope: str = "") -> str:
    return _toast_shell_css(
        scope,
        bg="#FFFFFF",
        text="#1C1917",
        border="#E7E5E4",
        shadow="0 10px 28px rgba(15, 23, 42, 0.12)",
        button="#64748B",
    )


def _dark_theme_toast_css(scope: str = "") -> str:
    return _toast_shell_css(
        scope,
        bg="#1E293B",
        text="#F8FAFC",
        border="#334155",
        shadow="0 10px 28px rgba(0, 0, 0, 0.42)",
        button="#94A3B8",
    )


def _dialog_css(scheme: str, scope: str = "") -> str:
    """st.dialog renderes i en portal med Streamlits lyse modal — tilpas i mørkt tema."""
    if scheme != "dark":
        return ""

    sp = f"{scope} " if scope else ""
    field_css = _dark_theme_field_css(f"{sp}[data-testid='stDialog']")
    return f"""
{sp}[data-testid="stDialog"] div[role="dialog"] {{
    background: var(--app-card-bg, #1A2332) !important;
    color: var(--app-text, #F8FAFC) !important;
    border: 1px solid var(--app-border, #334155) !important;
    box-shadow: 0 16px 48px rgba(0, 0, 0, 0.45) !important;
}}

{sp}[data-testid="stDialog"] div[role="dialog"] h1,
{sp}[data-testid="stDialog"] div[role="dialog"] h2,
{sp}[data-testid="stDialog"] div[role="dialog"] h3,
{sp}[data-testid="stDialog"] div[role="dialog"] h4,
{sp}[data-testid="stDialog"] div[role="dialog"] h5,
{sp}[data-testid="stDialog"] div[role="dialog"] h6,
{sp}[data-testid="stDialog"] div[role="dialog"] p,
{sp}[data-testid="stDialog"] div[role="dialog"] label,
{sp}[data-testid="stDialog"] div[role="dialog"] li,
{sp}[data-testid="stDialog"] div[role="dialog"] strong,
{sp}[data-testid="stDialog"] div[role="dialog"] .stMarkdown,
{sp}[data-testid="stDialog"] div[role="dialog"] .stMarkdown p,
{sp}[data-testid="stDialog"] div[role="dialog"] [data-testid="stMarkdownContainer"],
{sp}[data-testid="stDialog"] div[role="dialog"] [data-testid="stMarkdownContainer"] p,
{sp}[data-testid="stDialog"] div[role="dialog"] [data-testid="stCaptionContainer"],
{sp}[data-testid="stDialog"] div[role="dialog"] [data-testid="stCaptionContainer"] p,
{sp}[data-testid="stDialog"] div[role="dialog"] span:not(.status-pill):not(.admin-badge) {{
    color: var(--app-text, #F8FAFC) !important;
    -webkit-text-fill-color: var(--app-text, #F8FAFC) !important;
}}

{sp}[data-testid="stDialog"] button[aria-label="Close"],
{sp}[data-testid="stDialog"] button[aria-label="Luk"] {{
    color: var(--app-text-muted, #CBD5E1) !important;
}}

{sp}[data-testid="stDialog"] hr,
{sp}[data-testid="stDialog"] [data-testid="stDivider"] {{
    border-color: var(--app-border, #334155) !important;
}}

{sp}[data-testid="stDialog"] [data-testid="stAlert"],
{sp}[data-testid="stDialog"] [data-testid="stNotification"] {{
    background-color: var(--app-bg-secondary, #1E293B) !important;
    color: var(--app-text, #F8FAFC) !important;
    border-color: var(--app-border, #334155) !important;
}}

{sp}[data-testid="stDialog"] .admin-danger-zone {{
    background: rgba(127, 29, 29, 0.18) !important;
    border-color: rgba(239, 68, 68, 0.45) !important;
}}

{sp}[data-testid="stSelectboxVirtualDropdown"] {{
    z-index: 1000070 !important;
    background-color: #1E293B !important;
    color: #F8FAFC !important;
    border: 1px solid #334155 !important;
}}

{sp}[data-testid="stSelectboxVirtualDropdown"] [role="option"] {{
    color: #F8FAFC !important;
}}

{sp}[data-testid="stSelectboxVirtualDropdown"] [role="option"]:hover,
{sp}[data-testid="stSelectboxVirtualDropdown"] [role="option"][aria-selected="true"] {{
    background-color: #334155 !important;
    color: #F8FAFC !important;
}}

{field_css}
"""


def _dark_theme_tooltip_css(scope: str = "") -> str:
    sp = f"{scope} " if scope else ""
    return f"""
{sp}div[data-baseweb="tooltip"] > div,
{sp}div[data-baseweb="popover"]:has([data-testid="stTooltipContent"]) > div,
{sp}div[data-baseweb="popover"]:has(.stTooltipContent) > div,
{sp}div[role="tooltip"],
{sp}div[role="tooltip"] > div {{
    background-color: #1E293B !important;
    color: #F8FAFC !important;
    border: 1px solid #334155 !important;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.35) !important;
}}

{sp}div[data-baseweb="tooltip"],
{sp}div[role="tooltip"] {{
    color: #F8FAFC !important;
}}

{sp}[data-testid="stTooltipContent"],
{sp}.stTooltipContent,
{sp}[data-testid="stTooltipContent"] *,
{sp}.stTooltipContent *,
{sp}div[data-baseweb="tooltip"] *,
{sp}div[role="tooltip"] * {{
    color: #F8FAFC !important;
    -webkit-text-fill-color: #F8FAFC !important;
}}
"""


def _dark_theme_overrides_css() -> str:
    col_sel = _overview_columns_selector()
    overview_buttons = _overview_filter_button_selector()
    overview_secondary = _btn_secondary_selector(f".dark-theme {col_sel}")
    active_rules = _kpi_filter_active_color_rules(".dark-theme")
    return f"""
.dark-theme {{
    color-scheme: dark !important;
}}

{overview_secondary} {{
    background-color: #1E293B !important;
    color: #F8FAFC !important;
    border: 1px solid #334155 !important;
    -webkit-text-fill-color: #F8FAFC !important;
}}

.dark-theme {overview_buttons} {{
    height: 42px !important;
    min-height: 42px !important;
    max-height: 42px !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    font-size: 0.82rem !important;
    font-weight: 600 !important;
    line-height: 1.1 !important;
    box-shadow: none !important;
}}

{_dark_theme_field_css(".dark-theme")}

{active_rules}
"""


def _theme_dom_script(body: str) -> str:
    return f"""
(function () {{
  const doc = window.parent.document;
  const apply = () => {{
    const root = doc.querySelector(".stApp") || doc.body;
    if (!root) return false;
    {body}
    return true;
  }};
  if (apply()) return;
  const observer = new MutationObserver(() => {{
    if (apply()) observer.disconnect();
  }});
  observer.observe(doc.documentElement, {{ childList: true, subtree: true }});
  window.setTimeout(() => observer.disconnect(), 15000);
}})();
"""


def _theme_class_bootstrap(theme_choice: str) -> str:
    if theme_choice == "Lyst tema":
        return _theme_dom_script("""
    root.classList.remove("dark-theme");
    root.classList.add("light-theme");
""")
    if theme_choice == "Mørkt tema":
        return _theme_dom_script("""
    root.classList.remove("light-theme");
    root.classList.add("dark-theme");
""")
    return _theme_dom_script("""
    const dark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    root.classList.remove("light-theme", "dark-theme");
    root.classList.add(dark ? "dark-theme" : "light-theme");
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    if (!window.__borgerlisteThemeListener) {
      media.addEventListener("change", () => {
        const isDark = media.matches;
        root.classList.remove("light-theme", "dark-theme");
        root.classList.add(isDark ? "dark-theme" : "light-theme");
      });
      window.__borgerlisteThemeListener = true;
    }
""")


def _inject_theme_class(theme_choice: str) -> None:
    script = _theme_class_bootstrap(theme_choice)
    components.html(f"<script>{script}</script>", height=0, width=0)


def _dropdown_css(scheme: str) -> str:
    if scheme == "light":
        return """
div[data-baseweb="popover"],
div[data-baseweb="popover"] > div,
div[data-baseweb="popover"] ul,
div[data-baseweb="menu"],
div[data-baseweb="menu"] ul,
ul[role="listbox"],
li[role="option"] {
    background-color: #FFFFFF !important;
    color: #111827 !important;
}

div[data-baseweb="popover"] span,
div[data-baseweb="popover"] p,
div[data-baseweb="popover"] li,
div[data-baseweb="menu"] li,
div[data-baseweb="menu"] li span,
li[role="option"] span,
li[role="option"] p {
    color: #111827 !important;
}

li[role="option"]:hover,
li[role="option"][aria-selected="true"],
li[role="option"]:focus,
div[data-baseweb="menu"] li:hover,
div[data-baseweb="menu"] li[aria-selected="true"],
div[data-baseweb="menu"] li:focus {
    background-color: #F3F4F6 !important;
    color: #111827 !important;
}

li[role="option"]:hover span,
li[role="option"][aria-selected="true"] span,
div[data-baseweb="menu"] li:hover span,
div[data-baseweb="menu"] li[aria-selected="true"] span {
    color: #111827 !important;
}
"""
    return """
div[data-baseweb="popover"],
div[data-baseweb="popover"] > div,
div[data-baseweb="popover"] ul,
div[data-baseweb="menu"],
div[data-baseweb="menu"] ul,
ul[role="listbox"],
li[role="option"] {
    background-color: #1E293B !important;
    color: #F8FAFC !important;
}

div[data-baseweb="popover"] span,
div[data-baseweb="popover"] p,
div[data-baseweb="popover"] li,
div[data-baseweb="menu"] li,
div[data-baseweb="menu"] li span,
li[role="option"] span,
li[role="option"] p {
    color: #F8FAFC !important;
}

li[role="option"]:hover,
li[role="option"][aria-selected="true"],
li[role="option"]:focus,
div[data-baseweb="menu"] li:hover,
div[data-baseweb="menu"] li[aria-selected="true"],
div[data-baseweb="menu"] li:focus {
    background-color: #334155 !important;
    color: #F8FAFC !important;
}

li[role="option"]:hover span,
li[role="option"][aria-selected="true"] span,
div[data-baseweb="menu"] li:hover span,
div[data-baseweb="menu"] li[aria-selected="true"] span {
    color: #F8FAFC !important;
}
"""


def _wrap_media(css: str, media: str | None) -> str:
    if not media:
        return css
    return f"@media {media} {{\n{css}\n}}"


def _citizen_card_css() -> str:
    accent_rules: list[str] = []
    for filter_key, color in FILTER_ACTIVE_COLORS.items():
        accent_rules.append(
            f"""
.citizen-card-anchor[data-status="{filter_key}"] + [data-testid="stElementContainer"] [data-testid="stVerticalBlockBorderWrapper"] {{
    --app-card-accent-color: {color};
}}"""
        )
    return f"""
.citizen-card-anchor {{
    display: none !important;
}}

.citizen-card-anchor + [data-testid="stElementContainer"] [data-testid="stVerticalBlockBorderWrapper"] {{
    background: var(--app-card-bg) !important;
    border: var(--app-card-border-width) solid var(--app-card-border) !important;
    box-shadow: var(--app-card-shadow) !important;
    margin-bottom: var(--app-card-gap) !important;
    border-radius: 12px !important;
    border-left: var(--app-card-accent-width) solid var(--app-card-accent-color, {PRIMARY_COLOR}) !important;
    overflow: hidden;
}}

{"".join(accent_rules)}
"""


def _base_css_rules(browse_label: str) -> str:
    """Layout, upload-i18n og diskrete sidebar-knapper — bruges i alle temaer."""
    safe_label = browse_label.replace("\\", "\\\\").replace('"', '\\"')
    return f"""

#login-card-anchor + [data-testid="stElementContainer"] [data-testid="stVerticalBlockBorderWrapper"] {{
    background: var(--app-card-bg, #FFFFFF) !important;
    border: 1px solid var(--app-border, #E7E5E4) !important;
    border-radius: 18px !important;
    padding: 1.15rem 1.35rem 0.85rem !important;
    box-shadow: 0 16px 48px rgba(15, 23, 42, 0.08) !important;
}}

html:has(.dark-theme) #login-card-anchor + [data-testid="stElementContainer"] [data-testid="stVerticalBlockBorderWrapper"] {{
    box-shadow: 0 18px 52px rgba(0, 0, 0, 0.38) !important;
}}

.block-container {{
    max-width: 920px;
    padding-top: 1.25rem;
    padding-bottom: 2rem;
}}

.status-pill {{
    display: inline-block;
    padding: 0.25rem 0.65rem;
    border-radius: 999px;
    font-size: 0.75rem;
    font-weight: 700;
    line-height: 1.3;
    white-space: nowrap;
}}

.citizen-field {{
    display: flex;
    flex-wrap: wrap;
    gap: 0.25rem 0.65rem;
    margin: 0.2rem 0 0.55rem 0;
    line-height: 1.45;
}}

.citizen-field-label {{
    font-size: 0.78rem;
    font-weight: 600;
    color: var(--app-text-muted, rgba(255, 255, 255, 0.65));
    min-width: 6.75rem;
    flex: 0 0 auto;
}}

.citizen-field-value {{
    font-size: 0.95rem;
    color: var(--app-text, inherit);
    flex: 1 1 auto;
    word-break: break-word;
}}

.citizen-field-value--emphasis {{
    font-weight: 700;
    font-size: 1.02rem;
}}

.kpi-grid {{
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 0.75rem;
    margin: 0.5rem 0 1rem 0;
}}

.kpi-card {{
    background: var(--app-card-bg, #FFFFFF);
    border: 1px solid var(--app-card-border-subtle, rgba(0,0,0,0.08));
    box-shadow: var(--app-card-shadow, 0 1px 3px rgba(0,0,0,0.05));
    border-radius: 10px;
    padding: 0.85rem 0.6rem;
    text-align: center;
    min-width: 0;
}}

.kpi-number {{
    font-size: 2rem;
    font-weight: 700;
    line-height: 1.1;
    margin: 0.45rem 0 0 0;
    color: var(--app-text, #1C1917);
}}

.kpi-overview-card {{
    text-align: center;
    padding: 0.15rem 0;
}}

.kpi-overview-card .kpi-number {{
    margin-top: 0.45rem;
}}

{_overview_columns_selector()} {{
    min-width: 0;
}}

{_overview_filter_button_selector()} {{
    height: 42px !important;
    min-height: 42px !important;
    max-height: 42px !important;
    padding: 0 0.45rem !important;
    font-size: 0.82rem !important;
    font-weight: 600 !important;
    line-height: 1.1 !important;
    margin-top: 0.35rem !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    box-shadow: none !important;
}}

@media (max-width: 1024px) {{
    {_overview_columns_selector()} {{
        flex: 1 1 33% !important;
        min-width: 30% !important;
    }}
}}

@media (max-width: 768px) {{
    .kpi-overview-card .kpi-number {{
        font-size: 1.55rem;
    }}

    {_overview_filter_button_selector()} {{
        height: 42px !important;
        min-height: 42px !important;
        max-height: 42px !important;
        font-size: 0.78rem !important;
    }}
}}

.metric-number {{
    font-size: 1.75rem;
    font-weight: 700;
    line-height: 1.2;
    margin: 0;
}}

.page-info {{
    text-align: center;
    padding-top: 0.6rem;
    font-size: 0.95rem;
    line-height: 1.4;
}}

.upload-hint {{
    text-align: center;
    padding: 0.75rem 0 0.25rem 0;
    font-size: 0.92rem;
}}

[data-testid="stFileUploaderDropzoneInstructions"],
[data-testid="stFileUploaderDropzoneInstructions"] *,
[data-testid="stFileUploader"] small {{
    display: none !important;
}}

[data-testid="stFileUploader"] button {{
    font-size: 0 !important;
}}

[data-testid="stFileUploader"] button::after {{
    content: "{safe_label}";
    font-size: 0.9rem !important;
}}

.theme-mini [data-testid="stHorizontalBlock"] {{
    flex-wrap: nowrap !important;
    gap: 0.2rem !important;
}}

.theme-mini [data-testid="column"] {{
    min-width: 0 !important;
}}

.theme-mini .stButton > button {{
    background: transparent !important;
    border: 1px solid var(--app-border, #E7E5E4) !important;
    box-shadow: none !important;
    min-height: 2.1rem !important;
    padding: 0.15rem !important;
    font-size: 1rem !important;
    color: var(--app-text, #1C1917) !important;
    opacity: 0.6;
}}

.theme-mini .stButton > button[kind="primary"] {{
    background: rgba(37, 99, 235, 0.1) !important;
    border-color: {PRIMARY_COLOR} !important;
    opacity: 1;
}}

.lang-mini .stButton > button {{
    min-height: 2.2rem !important;
    font-size: 1.05rem !important;
    background: transparent !important;
    border: 1px solid var(--app-border, #E7E5E4) !important;
    box-shadow: none !important;
    color: var(--app-text, #1C1917) !important;
}}

.lang-mini .stButton > button[kind="primary"] {{
    background: rgba(37, 99, 235, 0.1) !important;
    border-color: {PRIMARY_COLOR} !important;
}}

[data-testid="stSidebar"] {{
    box-shadow: 10px 0 36px rgba(15, 23, 42, 0.07);
    border-right: 1px solid var(--app-border, #E7E5E4);
}}

[data-testid="stSidebar"] > div:first-child {{
    padding: 0.9rem 0.8rem 1.35rem !important;
    background: linear-gradient(
        180deg,
        var(--app-bg-secondary, #F5F5F4) 0%,
        var(--app-bg, #FAFAF9) 100%
    ) !important;
}}

html:has(.dark-theme) [data-testid="stSidebar"] {{
    box-shadow: 10px 0 40px rgba(0, 0, 0, 0.35);
}}

.sidebar-menu-label {{
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--app-text-muted, #64748B);
    margin: 0 0 0.35rem 0.2rem;
    line-height: 1.2;
}}

.sidebar-user-pill {{
    display: flex;
    flex-direction: column;
    gap: 0.12rem;
    padding: 0.62rem 0.72rem;
    margin: 0.15rem 0 0.65rem;
    border-radius: 12px;
    background: rgba(37, 99, 235, 0.07);
    border: 1px solid rgba(37, 99, 235, 0.14);
}}

.sidebar-user-name {{
    font-size: 0.88rem;
    font-weight: 700;
    color: var(--app-text, #1C1917);
    line-height: 1.25;
}}

.sidebar-user-role {{
    font-size: 0.72rem;
    font-weight: 600;
    color: var(--app-text-muted, #64748B);
    letter-spacing: 0.02em;
}}

.sidebar-license-badge {{
    display: inline-block;
    margin-top: 0.28rem;
    padding: 0.14rem 0.42rem;
    border-radius: 999px;
    font-size: 0.68rem;
    font-weight: 600;
    letter-spacing: 0.01em;
    color: var(--app-text-muted, #64748B);
    background: rgba(100, 116, 139, 0.12);
    border: 1px solid rgba(100, 116, 139, 0.18);
    line-height: 1.2;
    align-self: flex-start;
}}

.sidebar-divider-spacer {{
    height: 0.55rem;
}}

.sidebar-settings-panel {{
    margin-top: 0.15rem;
    padding-top: 0.55rem;
    border-top: 1px solid var(--app-border, #E7E5E4);
}}

[data-testid="stSidebar"] .stButton > button {{
    border-radius: 10px !important;
    min-height: 2.4rem !important;
    font-size: 0.88rem !important;
    font-weight: 600 !important;
    box-shadow: none !important;
    transition: background 0.15s ease, border-color 0.15s ease, color 0.15s ease;
}}

[data-testid="stSidebar"] .stButton > button[kind="secondary"],
[data-testid="stSidebar"] .stButton > button[data-testid="stBaseButton-secondary"] {{
    background: transparent !important;
    border: 1px solid transparent !important;
    color: var(--app-text-muted, #64748B) !important;
}}

[data-testid="stSidebar"] .stButton > button[kind="secondary"]:hover,
[data-testid="stSidebar"] .stButton > button[data-testid="stBaseButton-secondary"]:hover {{
    background: rgba(37, 99, 235, 0.06) !important;
    border-color: rgba(37, 99, 235, 0.12) !important;
    color: var(--app-text, #1C1917) !important;
}}

[data-testid="stSidebar"] .stButton > button[kind="primary"],
[data-testid="stSidebar"] .stButton > button[data-testid="stBaseButton-primary"] {{
    background: rgba(37, 99, 235, 0.12) !important;
    border: 1px solid rgba(37, 99, 235, 0.28) !important;
    color: {PRIMARY_COLOR} !important;
    font-weight: 700 !important;
}}

[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {{
    margin-bottom: 0.25rem;
}}

[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {{
    font-size: 0.68rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--app-text-muted, #64748B) !important;
    opacity: 0.85;
}}

[data-testid="stSidebar"] [data-testid="stExpander"] {{
    border: 1px solid var(--app-border, #E7E5E4) !important;
    border-radius: 10px !important;
    overflow: hidden;
    background: transparent !important;
}}

[data-testid="stSidebar"] [data-testid="stExpander"] summary {{
    font-size: 0.82rem !important;
    font-weight: 600 !important;
    padding: 0.45rem 0.55rem !important;
}}

[data-testid="stSidebar"] hr {{
    margin: 0.5rem 0 !important;
    opacity: 0.25;
}}

.borgerliste-pin-bridge {{
    display: none !important;
}}

[data-testid="stSidebar"] .st-key-borgerliste_pin_bridge {{
    position: fixed !important;
    left: -10000px !important;
    top: 0 !important;
    width: 1px !important;
    height: 1px !important;
    overflow: hidden !important;
    opacity: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
    border: none !important;
    z-index: -1 !important;
    clip: rect(0, 0, 0, 0) !important;
}}

[data-testid="stSidebar"] .st-key-borgerliste_pin_bridge [data-testid="stButton"] > button {{
    min-height: 0 !important;
    height: 1px !important;
    width: 1px !important;
    padding: 0 !important;
    font-size: 0 !important;
    line-height: 0 !important;
    border: none !important;
    background: transparent !important;
}}

.borgerliste-pin-host {{
    display: inline-flex !important;
    align-items: center !important;
    gap: 0.2rem !important;
    vertical-align: middle !important;
}}

.borgerliste-header-pin {{
    display: inline-flex;
    align-items: center;
    justify-content: center;
    box-sizing: border-box;
    padding: 0;
    margin: 0;
    border: none;
    background: transparent;
    color: inherit;
    cursor: pointer;
    opacity: 0.72;
    flex: 0 0 auto;
    line-height: 1;
    pointer-events: auto;
    transition: background 0.15s ease, opacity 0.15s ease, color 0.15s ease;
}}

.borgerliste-header-pin:hover {{
    opacity: 1;
    background: rgba(128, 131, 145, 0.14);
}}

.borgerliste-header-pin.is-pinned {{
    opacity: 1;
    color: {PRIMARY_COLOR};
}}

.borgerliste-header-pin svg {{
    display: block;
    width: 1.125rem;
    height: 1.125rem;
    fill: currentColor;
}}

[data-testid="stAppViewContainer"] iframe[height="0"] {{
    pointer-events: none !important;
}}

@media (max-width: 1024px) {{
    .kpi-grid {{
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }}
}}

@media (max-width: 768px) {{
    .block-container {{
        padding-left: 0.65rem;
        padding-right: 0.65rem;
    }}

    [data-testid="stSidebar"] {{
        z-index: 999990 !important;
    }}

    [data-testid="stSidebar"] > div:first-child {{
        padding: 0.75rem 0.65rem 1rem !important;
    }}

    [data-testid="stAppViewContainer"] [data-testid="stMain"],
    [data-testid="stAppViewContainer"] [data-testid="stMain"] > div {{
        width: 100% !important;
        max-width: 100% !important;
    }}

    [data-testid="stSidebarBackdrop"] {{
        z-index: 999985 !important;
    }}

    .kpi-grid {{
        grid-template-columns: 1fr;
        gap: 0.55rem;
    }}

    .kpi-card {{
        padding: 0.75rem 0.65rem;
    }}

    .kpi-number {{
        font-size: 1.65rem;
    }}

    .stButton > button,
    .stDownloadButton > button,
    div[data-testid="stSelectbox"] div[data-baseweb="select"],
    div[data-testid="stTextInput"] input {{
        min-height: 2.85rem !important;
        font-size: 1rem !important;
    }}

    .metric-number {{
        font-size: 1.5rem;
    }}
}}
"""


def _admin_badge_css(scheme: str) -> str:
    if scheme == "dark":
        return """
.admin-badge {
    display: inline-block;
    padding: 0.2rem 0.55rem;
    border-radius: 999px;
    font-size: 0.72rem;
    font-weight: 700;
    line-height: 1.3;
    white-space: nowrap;
    border: 1px solid transparent;
}
.admin-badge--role-admin {
    background: #1E3A8A !important;
    color: #DBEAFE !important;
    border-color: #3B82F6 !important;
}
.admin-badge--role-user {
    background: #334155 !important;
    color: #E2E8F0 !important;
    border-color: #64748B !important;
}
.admin-badge--license-paid {
    background: #14532D !important;
    color: #BBF7D0 !important;
    border-color: #22C55E !important;
}
.admin-badge--license-trial {
    background: #78350F !important;
    color: #FDE68A !important;
    border-color: #F59E0B !important;
}
.admin-badge--license-expired {
    background: #7F1D1D !important;
    color: #FECACA !important;
    border-color: #EF4444 !important;
}
.admin-badge--license-admin {
    background: #312E81 !important;
    color: #E0E7FF !important;
    border-color: #6366F1 !important;
}
.admin-municipality-none {
    color: var(--app-text-muted, #94A3B8);
    font-size: 0.85rem;
}
.admin-municipality-group {
    display: inline-flex;
    flex-wrap: wrap;
    gap: 0.25rem;
}
.admin-municipality-badge {
    background: #1E293B !important;
    color: #CBD5E1 !important;
    border-color: #475569 !important;
}
.admin-user-inactive {
    opacity: 0.55;
    text-decoration: line-through;
}
.admin-users-table-header {
    font-size: 0.78rem;
    font-weight: 700;
    color: var(--app-text-muted, #94A3B8);
    letter-spacing: 0.02em;
    text-transform: uppercase;
    padding-bottom: 0.35rem;
    border-bottom: 1px solid var(--app-border, #334155);
    margin-bottom: 0.15rem;
}
.admin-users-table-row {
    padding: 0.35rem 0;
    border-bottom: 1px solid var(--app-border, #334155);
    align-items: center;
}
.admin-danger-zone {
    margin-top: 0.75rem;
    padding: 0.85rem 0.95rem;
    border-radius: 10px;
    border: 1px solid rgba(239, 68, 68, 0.35);
    background: rgba(127, 29, 29, 0.12);
}
.admin-danger-zone-title {
    color: #FCA5A5;
    font-size: 0.82rem;
    font-weight: 700;
    margin-bottom: 0.35rem;
}
"""
    return """
.admin-badge {
    display: inline-block;
    padding: 0.2rem 0.55rem;
    border-radius: 999px;
    font-size: 0.72rem;
    font-weight: 700;
    line-height: 1.3;
    white-space: nowrap;
    border: 1px solid transparent;
}
.admin-badge--role-admin {
    background: #DBEAFE !important;
    color: #1E40AF !important;
    border-color: #93C5FD !important;
}
.admin-badge--role-user {
    background: #F1F5F9 !important;
    color: #475569 !important;
    border-color: #CBD5E1 !important;
}
.admin-badge--license-paid {
    background: #DCFCE7 !important;
    color: #166534 !important;
    border-color: #86EFAC !important;
}
.admin-badge--license-trial {
    background: #FEF3C7 !important;
    color: #92400E !important;
    border-color: #FCD34D !important;
}
.admin-badge--license-expired {
    background: #FEE2E2 !important;
    color: #991B1B !important;
    border-color: #FCA5A5 !important;
}
.admin-badge--license-admin {
    background: #E0E7FF !important;
    color: #3730A3 !important;
    border-color: #A5B4FC !important;
}
.admin-municipality-none {
    color: var(--app-text-muted, #64748B);
    font-size: 0.85rem;
}
.admin-municipality-group {
    display: inline-flex;
    flex-wrap: wrap;
    gap: 0.25rem;
}
.admin-municipality-badge {
    background: #F8FAFC !important;
    color: #475569 !important;
    border-color: #CBD5E1 !important;
}
.admin-user-inactive {
    opacity: 0.55;
    text-decoration: line-through;
}
.admin-users-table-header {
    font-size: 0.78rem;
    font-weight: 700;
    color: var(--app-text-muted, #64748B);
    letter-spacing: 0.02em;
    text-transform: uppercase;
    padding-bottom: 0.35rem;
    border-bottom: 1px solid var(--app-border, #E7E5E4);
    margin-bottom: 0.15rem;
}
.admin-users-table-row {
    padding: 0.35rem 0;
    border-bottom: 1px solid var(--app-border, #E7E5E4);
    align-items: center;
}
.admin-danger-zone {
    margin-top: 0.75rem;
    padding: 0.85rem 0.95rem;
    border-radius: 10px;
    border: 1px solid rgba(239, 68, 68, 0.35);
    background: rgba(254, 226, 226, 0.45);
}
.admin-danger-zone-title {
    color: #B91C1C;
    font-size: 0.82rem;
    font-weight: 700;
    margin-bottom: 0.35rem;
}
"""


def _account_section_css(scheme: str) -> str:
    if scheme == "dark":
        panel_bg = "transparent"
        divider = "var(--app-border, #334155)"
        gdpr_header_bg = "#1E293B"
        gdpr_row_border = "#334155"
        danger_bg = "rgba(127, 29, 29, 0.12)"
        danger_border = "rgba(239, 68, 68, 0.35)"
        danger_title = "#FCA5A5"
        metric_value = "#F8FAFC"
        metric_label = "#94A3B8"
    else:
        panel_bg = "transparent"
        divider = "var(--app-border, #E7E5E4)"
        gdpr_header_bg = "#F8FAFC"
        gdpr_row_border = "#E7E5E4"
        danger_bg = "rgba(254, 226, 226, 0.45)"
        danger_border = "rgba(239, 68, 68, 0.35)"
        danger_title = "#B91C1C"
        metric_value = "#0F172A"
        metric_label = "#64748B"

    return f"""
.account-section {{
    margin-bottom: 0.5rem;
}}
.account-panel {{
    margin-bottom: 1.25rem;
}}
.account-panel-divider {{
    border-top: 1px solid {divider};
    margin: 1.25rem 0;
}}
[data-testid="stTabs"] h4 {{
    font-size: 1.05rem !important;
    font-weight: 700 !important;
    margin-bottom: 0.35rem !important;
    margin-top: 0 !important;
}}
[data-testid="stTabs"] [data-testid="stCaptionContainer"] {{
    margin-bottom: 0.65rem !important;
}}
[data-testid="stTabs"] [data-testid="stForm"] {{
    border: none !important;
    padding: 0 !important;
    background: {panel_bg} !important;
    box-shadow: none !important;
}}
.account-table-header {{
    font-size: 0.78rem;
    font-weight: 700;
    color: var(--app-text-muted);
    letter-spacing: 0.02em;
    text-transform: uppercase;
    padding-bottom: 0.35rem;
    border-bottom: 1px solid {divider};
    margin-bottom: 0.15rem;
}}
.account-table-row {{
    padding: 0.35rem 0;
    border-bottom: 1px solid {divider};
    font-size: 0.9rem;
    line-height: 1.45;
    display: flex;
    align-items: center;
    min-height: 2rem;
}}
div[data-testid="stVerticalBlock"]:has(> .account-table-btn-marker) .stButton > button {{
    white-space: nowrap !important;
    min-width: max-content !important;
    width: auto !important;
}}
div[data-testid="stVerticalBlock"]:has(> .account-inline-form-marker) [data-testid="stFormSubmitButton"] > button {{
    white-space: nowrap !important;
    min-width: max-content !important;
    width: auto !important;
    margin-top: 1.75rem !important;
}}
.account-metric-inline {{
    display: flex;
    align-items: baseline;
    gap: 0.65rem;
    padding: 0.75rem 0 0.35rem;
}}
.account-metric-value {{
    font-size: 2rem;
    font-weight: 800;
    line-height: 1;
    color: {metric_value};
}}
.account-metric-label {{
    font-size: 0.9rem;
    color: {metric_label};
}}
.account-danger-panel {{
    margin-top: 1.25rem;
    padding: 1rem 0 0;
    border-top: 1px solid {danger_border};
}}
.account-danger-panel h4,
.account-danger-panel .account-danger-panel-title {{
    color: {danger_title} !important;
    font-size: 0.95rem !important;
    margin-bottom: 0.35rem !important;
}}
[data-testid="stTabs"] [data-testid="stMarkdownContainer"] table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 0.88rem;
    margin-top: 0.35rem;
    border: 1px solid {divider};
    border-radius: 8px;
    overflow: hidden;
}}
[data-testid="stTabs"] [data-testid="stMarkdownContainer"] table thead th,
[data-testid="stTabs"] [data-testid="stMarkdownContainer"] table tr:first-child td {{
    background: {gdpr_header_bg};
    font-weight: 700;
    text-align: left;
    padding: 0.55rem 0.75rem;
    border-bottom: 1px solid {gdpr_row_border};
}}
[data-testid="stTabs"] [data-testid="stMarkdownContainer"] table td {{
    padding: 0.5rem 0.75rem;
    border-bottom: 1px solid {gdpr_row_border};
    vertical-align: top;
}}
[data-testid="stTabs"] [data-testid="stMarkdownContainer"] table tr:last-child td {{
    border-bottom: none;
}}
.account-gdpr-table-note {{
    margin-top: 0.35rem;
}}
"""


def _themed_css_rules(
    palette: dict[str, str],
    button_secondary_bg: str,
    media: str | None = None,
) -> str:
    """Nordic Light eller mørkt tema — tilpassede farver og kontraster."""
    card_shadow = palette.get("card_shadow", "none")
    card_border_subtle = palette.get("card_border_subtle", palette["border"])
    card_border = palette.get("card_border", palette["border"])
    card_border_width = palette.get("card_border_width", "1px")
    card_gap = palette.get("card_gap", "1rem")
    card_accent_width = palette.get("card_accent_width", "4px")
    btn_secondary = _btn_secondary_selector()
    btn_primary = _btn_primary_selector()
    rules = f"""
:root {{
    color-scheme: {palette["color_scheme"]};
    --app-bg: {palette["bg"]};
    --app-bg-secondary: {palette["bg_secondary"]};
    --app-card-bg: {palette["card_bg"]};
    --app-input-bg: {palette["input_bg"]};
    --app-text: {palette["text"]};
    --app-text-muted: {palette["text_muted"]};
    --app-border: {palette["border"]};
    --app-card-shadow: {card_shadow};
    --app-card-border-subtle: {card_border_subtle};
    --app-card-border: {card_border};
    --app-card-border-width: {card_border_width};
    --app-card-gap: {card_gap};
    --app-card-accent-width: {card_accent_width};
}}

.stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"],
[data-testid="stHeader"], .block-container {{
    background-color: var(--app-bg) !important;
    color: var(--app-text) !important;
}}

[data-testid="stSidebar"], [data-testid="stSidebar"] > div:first-child {{
    background-color: var(--app-bg-secondary) !important;
    color: var(--app-text) !important;
}}

h1, h2, h3, h4, h5, h6, p, label, li, strong,
.stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6,
.stApp p, .stApp label, .stApp li, .stApp strong,
.stMarkdown, .stMarkdown p, .stCaption,
[data-testid="stMarkdownContainer"], [data-testid="stMarkdownContainer"] p,
[data-testid="stSidebar"] label, [data-testid="stSidebar"] p,
[data-testid="stSidebar"] span:not(.status-pill), [data-testid="stRadio"] label,
.stApp span:not(.status-pill) {{
    color: var(--app-text) !important;
}}

.metric-number, .page-info, .page-info b, .upload-hint, .kpi-number {{
    color: var(--app-text) !important;
}}

div[data-testid="element-container"] div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlockBorderWrapper"],
.kpi-card {{
    background: var(--app-card-bg) !important;
    border: 1px solid var(--app-card-border-subtle) !important;
    box-shadow: var(--app-card-shadow) !important;
}}

div[data-testid="stTextInput"] input,
div[data-testid="stSelectbox"] div[data-baseweb="select"],
div[data-testid="stMultiSelect"] div[data-baseweb="select"],
div[data-baseweb="input"] input,
div[data-testid="stNumberInput"] input,
div[data-baseweb="select"] > div,
div[data-baseweb="select"] {{
    background-color: var(--app-input-bg) !important;
    color: var(--app-text) !important;
    border: 1px solid var(--app-border) !important;
}}

{_dropdown_css(palette["color_scheme"])}

{_status_pill_css(palette["color_scheme"])}

{_admin_badge_css(palette["color_scheme"])}

{_account_section_css(palette["color_scheme"])}

{btn_secondary},
[data-testid="stFileUploader"] button {{
    border: 1px solid var(--app-border) !important;
    background-color: {button_secondary_bg} !important;
    color: var(--app-text) !important;
    box-shadow: none !important;
}}

{btn_primary},
.stDownloadButton > button,
div[data-testid="stFormSubmitButton"] > button {{
    background-color: {PRIMARY_COLOR} !important;
    color: {PRIMARY_TEXT} !important;
    border-color: {PRIMARY_COLOR} !important;
    box-shadow: none !important;
}}

.stButton > button:disabled,
.stButton button[data-testid="stBaseButton-secondary"]:disabled,
.stButton button[data-testid="stBaseButton-primary"]:disabled {{
    opacity: 0.45;
}}

section[data-testid="stFileUploaderDropzone"] {{
    background: var(--app-card-bg) !important;
    border: 1px dashed var(--app-border) !important;
}}

[data-testid="stFileUploader"] button::after {{
    color: var(--app-text) !important;
}}

[data-testid="stExpander"] details,
[data-testid="stExpander"] summary,
[data-testid="stExpander"] summary span {{
    background-color: var(--app-card-bg) !important;
    color: var(--app-text) !important;
    border-color: var(--app-border) !important;
}}

[data-testid="stAlert"],
[data-testid="stNotification"] {{
    background-color: var(--app-card-bg) !important;
    color: var(--app-text) !important;
    border-color: var(--app-border) !important;
}}

[data-testid="stToast"],
.stToast {{
    background-color: var(--app-card-bg) !important;
    color: var(--app-text) !important;
    border: 1px solid var(--app-border) !important;
    border-radius: 0.65rem !important;
    overflow: hidden !important;
}}

[data-testid="stToast"] > div,
[data-testid="stToast"] div,
.stToast > div,
.stToast div {{
    background: transparent !important;
    background-color: transparent !important;
    border: none !important;
    box-shadow: none !important;
    outline: none !important;
}}

[data-testid="stToast"] *,
.stToast * {{
    color: var(--app-text) !important;
    -webkit-text-fill-color: var(--app-text) !important;
}}

div[data-baseweb="select"] svg {{
    fill: var(--app-text) !important;
}}

.theme-mini .stButton > button,
.lang-mini .stButton > button {{
    background: transparent !important;
    border: 1px solid var(--app-border) !important;
    color: var(--app-text) !important;
}}

.theme-mini .stButton > button[kind="primary"],
.lang-mini .stButton > button[kind="primary"] {{
    background: rgba(37, 99, 235, 0.12) !important;
    border-color: {PRIMARY_COLOR} !important;
    color: var(--app-text) !important;
}}
"""
    return _wrap_media(rules, media)


def _login_page_css() -> str:
    return """
html:has(#login-page-anchor) [data-testid="stSidebar"] > div:first-child {
    padding-top: 1rem;
}

html:has(#login-page-anchor) .block-container {
    padding-top: 2.5rem;
    padding-bottom: 3rem;
}

.login-hero {
    text-align: center;
    margin: 0 auto 1.75rem;
    max-width: 26rem;
}

.login-logo-wrap {
    display: flex;
    justify-content: center;
    margin-bottom: 1.1rem;
}

.login-logo-wrap img,
.login-logo-wrap svg {
    width: 6.5rem;
    height: 6.5rem;
    filter: drop-shadow(0 10px 24px rgba(37, 99, 235, 0.28));
}

.login-brand-title {
    font-size: 2.15rem;
    font-weight: 800;
    letter-spacing: -0.03em;
    line-height: 1.15;
    margin: 0 0 0.35rem 0;
    color: var(--app-text, #1C1917);
}

.login-brand-subtitle {
    font-size: 1.02rem;
    line-height: 1.45;
    margin: 0;
    color: var(--app-text-muted, #64748B);
}

html:has(#login-page-anchor) [data-testid="stFormSubmitButton"] > button {
    margin-top: 0.35rem;
    min-height: 2.75rem !important;
    font-weight: 600 !important;
    border-radius: 10px !important;
}

@media (max-width: 768px) {
    html:has(#login-page-anchor) .block-container {
        padding-top: 1.5rem;
    }

    .login-brand-title {
        font-size: 1.75rem;
    }
}
"""


def inject_styles(theme_choice: str) -> None:
    """Indsprøjter CSS i præcis én <style>-blok — aldrig synlig rå tekst."""
    css_parts = [_base_css_rules(t("upload_browse")), _citizen_card_css(), _login_page_css()]

    if theme_choice == "Browser standard":
        light = THEME_PALETTES["Lyst tema"]
        dark = THEME_PALETTES["Mørkt tema"]
        css_parts.append(_themed_css_rules(light, light["input_bg"], media="(prefers-color-scheme: light)"))
        css_parts.append(_themed_css_rules(dark, dark["input_bg"], media="(prefers-color-scheme: dark)"))
        css_parts.append(_wrap_media(_light_theme_overrides_css(), "(prefers-color-scheme: light)"))
        css_parts.append(_wrap_media(_light_theme_field_css("html:has(.stApp.light-theme)"), "(prefers-color-scheme: light)"))
        css_parts.append(_wrap_media(_light_theme_tooltip_css("html:has(.stApp.light-theme)"), "(prefers-color-scheme: light)"))
        css_parts.append(_wrap_media(_light_theme_toast_css("html:has(.stApp.light-theme)"), "(prefers-color-scheme: light)"))
        css_parts.append(_wrap_media(_dark_theme_overrides_css(), "(prefers-color-scheme: dark)"))
        css_parts.append(_wrap_media(_dark_theme_field_css("html:has(.stApp.dark-theme)"), "(prefers-color-scheme: dark)"))
        css_parts.append(_wrap_media(_dark_theme_tooltip_css("html:has(.stApp.dark-theme)"), "(prefers-color-scheme: dark)"))
        css_parts.append(_wrap_media(_dark_theme_toast_css("html:has(.stApp.dark-theme)"), "(prefers-color-scheme: dark)"))
        css_parts.append(_wrap_media(_dialog_css("dark", "html:has(.stApp.dark-theme)"), "(prefers-color-scheme: dark)"))
    elif theme_choice in THEME_PALETTES:
        palette = THEME_PALETTES[theme_choice]
        is_light = theme_choice == "Lyst tema"
        button_secondary_bg = "#FFFFFF" if is_light else palette["input_bg"]
        css_parts.append(_themed_css_rules(palette, button_secondary_bg))
        if is_light:
            css_parts.append(_light_theme_overrides_css())
            css_parts.append(_light_theme_field_css())
            css_parts.append(_light_theme_tooltip_css())
            css_parts.append(_light_theme_toast_css())
        else:
            css_parts.append(_dark_theme_overrides_css())
            css_parts.append(_dark_theme_field_css())
            css_parts.append(_dark_theme_tooltip_css())
            css_parts.append(_dark_theme_toast_css())
            css_parts.append(_dark_theme_toast_css(".dark-theme"))
            css_parts.append(_dialog_css("dark", "html:has(.stApp.dark-theme)"))

    css = "<style>\n" + "\n".join(css_parts) + "\n</style>"
    st.markdown(css, unsafe_allow_html=True)
    _inject_theme_class(theme_choice)


def inject_sidebar_controls(
    delay_seconds: int = SIDEBAR_AUTO_COLLAPSE_SECONDS,
    *,
    pinned: bool = False,
    show_pin: bool = False,
    pin_label: str = "",
    unpin_label: str = "",
) -> None:
    """Header-pin ved sidebar-toggle + auto-luk (letvægts, uden DOM-overvågning)."""
    delay_ms = max(1, int(delay_seconds)) * 1000
    pinned_js = "true" if pinned else "false"
    show_pin_js = "true" if show_pin else "false"
    pin_svg = (
        '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">'
        '<path d="M16 9V4h1c.55 0 1-.45 1-1s-.45-1-1-1H7c-.55 0-1 .45-1 1s.45 1 1 1h1v5c0 1.66-1.34 3-3 3v2h5.97v7l1 1 1-1v-7H19v-2c-1.66 0-3-1.34-3-3z"/>'
        "</svg>"
    )
    components.html(
        f"""
        <script>
        (function() {{
            const win = window.parent;
            const doc = win.document;
            const cfg = win.__borgerlisteSidebar || (win.__borgerlisteSidebar = {{}});
            if (cfg.pinObserver) {{
                cfg.pinObserver.disconnect();
                delete cfg.pinObserver;
            }}
            cfg.delay = {delay_ms};
            cfg.pinned = {pinned_js};
            cfg.showPin = {show_pin_js};
            cfg.pinLabel = {json.dumps(pin_label)};
            cfg.unpinLabel = {json.dumps(unpin_label)};
            cfg.pinIcon = {json.dumps(pin_svg)};

            if (!cfg.ready) {{
                cfg.ready = true;

                cfg.isMobile = function() {{
                    return !!win.matchMedia && win.matchMedia('(max-width: 768px)').matches;
                }};

                cfg.effectivePinned = function() {{
                    // Pin er desktop-only — på mobil må sidebaren ikke genåbnes ved hvert klik.
                    return !!cfg.pinned && !cfg.isMobile();
                }};

                cfg.isSidebarExpanded = function() {{
                    const sidebar = doc.querySelector('[data-testid="stSidebar"]');
                    return !!sidebar && sidebar.getBoundingClientRect().width > 48;
                }};

                cfg.findSidebarToggleButton = function() {{
                    const byTestId = doc.querySelector('[data-testid="stSidebarCollapseButton"]')
                        || doc.querySelector('[data-testid="stExpandSidebarButton"]')
                        || doc.querySelector('[data-testid="collapsedControl"] button');
                    if (byTestId) return byTestId;

                    const pickToggle = (root) => Array.from(root.querySelectorAll('button')).find((btn) => {{
                        if (btn.id === 'borgerliste-sidebar-pin') return false;
                        const label = (btn.getAttribute('aria-label') || btn.textContent || '').toLowerCase();
                        return (
                            label.includes('keyboard_double_arrow_left')
                            || label.includes('keyboard_double_arrow_right')
                            || label.includes('collapse')
                            || label.includes('expand')
                        );
                    }}) || null;

                    const sidebar = doc.querySelector('[data-testid="stSidebar"]');
                    if (sidebar) {{
                        const inSidebar = pickToggle(sidebar);
                        if (inSidebar) return inSidebar;
                    }}

                    const header = doc.querySelector('[data-testid="stHeader"]');
                    if (header) return pickToggle(header);
                    return null;
                }};

                cfg.findSidebarButton = function(kind) {{
                    if (kind === 'collapse' || kind === 'keyboard_double_arrow_left') {{
                        const collapse = doc.querySelector('[data-testid="stSidebarCollapseButton"]');
                        if (collapse) return collapse;
                    }}
                    if (kind === 'expand' || kind === 'keyboard_double_arrow_right') {{
                        const expand = doc.querySelector('[data-testid="stExpandSidebarButton"]');
                        if (expand) return expand;
                    }}
                    return Array.from(doc.querySelectorAll('button')).find((btn) => {{
                        if (btn.id === 'borgerliste-sidebar-pin') return false;
                        const label = (btn.getAttribute('aria-label') || btn.textContent || '').toLowerCase();
                        return label.includes(kind);
                    }}) || null;
                }};

                cfg.triggerPinToggle = function() {{
                    const bridge = doc.querySelector('.st-key-borgerliste_pin_bridge button')
                        || doc.querySelector('[data-testid="stSidebar"] .st-key-borgerliste_pin_bridge button');
                    if (bridge) {{
                        bridge.click();
                        return;
                    }}
                    win.setTimeout(() => {{
                        doc.querySelector('.st-key-borgerliste_pin_bridge button')?.click();
                    }}, 120);
                }};

                cfg.syncPinButtonSize = function(toggleBtn, pinBtn) {{
                    if (!toggleBtn || !pinBtn) return;
                    const rect = toggleBtn.getBoundingClientRect();
                    if (rect.width > 0) {{
                        pinBtn.style.width = `${{rect.width}}px`;
                        pinBtn.style.height = `${{rect.height}}px`;
                        pinBtn.style.minWidth = `${{rect.width}}px`;
                        pinBtn.style.minHeight = `${{rect.height}}px`;
                    }}
                    const toggleStyle = win.getComputedStyle(toggleBtn);
                    pinBtn.style.borderRadius = toggleStyle.borderRadius;
                }};

                cfg.updatePinButton = function() {{
                    const oldRow = doc.getElementById('borgerliste-header-pin-row');
                    if (oldRow?.parentElement) {{
                        while (oldRow.firstChild) {{
                            oldRow.parentElement.insertBefore(oldRow.firstChild, oldRow);
                        }}
                        oldRow.remove();
                    }}

                    const showPin = cfg.showPin && !cfg.isMobile();
                    if (!showPin) {{
                        doc.getElementById('borgerliste-sidebar-pin')?.remove();
                        return;
                    }}

                    const toggleBtn = cfg.findSidebarToggleButton();
                    if (!toggleBtn?.parentElement) return;

                    toggleBtn.parentElement.classList.add('borgerliste-pin-host');

                    let pinBtn = doc.getElementById('borgerliste-sidebar-pin');
                    if (!pinBtn) {{
                        pinBtn = doc.createElement('button');
                        pinBtn.id = 'borgerliste-sidebar-pin';
                        pinBtn.type = 'button';
                        pinBtn.className = 'borgerliste-header-pin';
                        pinBtn.addEventListener('click', (event) => {{
                            event.preventDefault();
                            event.stopPropagation();
                            cfg.triggerPinToggle();
                        }});
                        toggleBtn.parentElement.insertBefore(pinBtn, toggleBtn);
                    }} else if (pinBtn.nextElementSibling !== toggleBtn) {{
                        toggleBtn.parentElement.insertBefore(pinBtn, toggleBtn);
                    }}

                    pinBtn.innerHTML = cfg.pinIcon;
                    pinBtn.classList.toggle('is-pinned', cfg.pinned);
                    pinBtn.setAttribute('aria-label', cfg.pinned ? cfg.unpinLabel : cfg.pinLabel);
                    pinBtn.setAttribute('title', cfg.pinned ? cfg.unpinLabel : cfg.pinLabel);
                    cfg.syncPinButtonSize(toggleBtn, pinBtn);
                }};

                cfg.collapseSidebar = function() {{
                    if (cfg.effectivePinned() || !cfg.isSidebarExpanded()) return;
                    const btn = cfg.findSidebarButton('keyboard_double_arrow_left') || cfg.findSidebarButton('collapse');
                    if (btn) btn.click();
                }};

                cfg.scheduleCollapse = function() {{
                    if (cfg.effectivePinned()) {{
                        if (cfg.timer) win.clearTimeout(cfg.timer);
                        cfg.timer = null;
                        return;
                    }}
                    if (cfg.timer) win.clearTimeout(cfg.timer);
                    if (!cfg.isSidebarExpanded()) return;
                    cfg.timer = win.setTimeout(() => cfg.collapseSidebar(), cfg.delay);
                }};

                cfg.bindSidebarOnce = function() {{
                    const sidebar = doc.querySelector('[data-testid="stSidebar"]');
                    if (!sidebar || sidebar.dataset.autoCollapseBound === '1') return;
                    sidebar.dataset.autoCollapseBound = '1';
                    sidebar.addEventListener('mouseenter', () => {{
                        if (cfg.timer) win.clearTimeout(cfg.timer);
                    }});
                    sidebar.addEventListener('mouseleave', () => cfg.scheduleCollapse());
                    sidebar.addEventListener('focusin', () => {{
                        if (cfg.timer) win.clearTimeout(cfg.timer);
                    }});
                    sidebar.addEventListener('focusout', () => cfg.scheduleCollapse());
                }};

                cfg.refresh = function() {{
                    cfg.updatePinButton();
                    // Pin må ikke force-expande ved hvert rerun — det genåbnede mobil-sidebaren ved hvert tryk.
                    if (cfg.effectivePinned()) {{
                        if (cfg.timer) win.clearTimeout(cfg.timer);
                        cfg.timer = null;
                        return;
                    }}
                    cfg.bindSidebarOnce();
                    if (cfg.isMobile() && cfg.isSidebarExpanded()) {{
                        // Efter navigation/klik: luk drawer på mobil, så den kun åbnes via toggle.
                        cfg.collapseSidebar();
                        return;
                    }}
                    cfg.scheduleCollapse();
                }};
            }}

            cfg.refresh();
            win.setTimeout(() => cfg.refresh(), 180);
        }})();
        </script>
        """,
        height=0,
    )

