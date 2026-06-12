from __future__ import annotations

import streamlit as st


def svg_icon(name: str, size: int = 18) -> str:
    icons = {
        "database": '<path d="M4 6c0-1.7 3.6-3 8-3s8 1.3 8 3-3.6 3-8 3-8-1.3-8-3Z"/><path d="M4 6v6c0 1.7 3.6 3 8 3s8-1.3 8-3V6"/><path d="M4 12v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6"/>',
        "image": '<rect x="3" y="5" width="18" height="14" rx="3"/><circle cx="8" cy="10" r="1.5"/><path d="m5 17 5-5 4 4 2-2 3 3"/>',
        "text": '<path d="M5 6h14"/><path d="M5 10h10"/><path d="M5 14h14"/><path d="M5 18h8"/>',
        "missing": '<rect x="4" y="4" width="16" height="16" rx="3"/><path d="m7 17 10-10"/><path d="m8 8 8 8"/>',
        "anchor": '<path d="M12 4v16"/><path d="M8 8h8"/><path d="M7 16c1 2.7 3.2 4 5 4s4-1.3 5-4"/><circle cx="12" cy="4" r="2"/>',
        "settings": '<path d="M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V22a2 2 0 1 1-4 0v-.2a1.7 1.7 0 0 0-1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.2a1.7 1.7 0 0 0 1.5-1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3h.1a1.7 1.7 0 0 0 1-1.5V2a2 2 0 1 1 4 0v.2a1.7 1.7 0 0 0 1 1.5h.1a1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8v.1a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.2a1.7 1.7 0 0 0-1.4 1Z"/>',
        "download": '<path d="M12 3v12"/><path d="m7 10 5 5 5-5"/><path d="M5 21h14"/>',
    }
    body = icons.get(name, icons["database"])
    return (
        f'<svg class="ui-icon" width="{size}" height="{size}" viewBox="0 0 24 24" '
        f'fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
        f'stroke-linejoin="round" aria-hidden="true">{body}</svg>'
    )


def theme_vars(theme: str) -> dict[str, str]:
    if theme == "light":
        return {
            "scheme": "light",
            "bg": "#ffffff",
            "panel": "#ffffff",
            "panel2": "#f7f2ff",
            "line": "rgba(88, 65, 140, .16)",
            "line_strong": "rgba(88, 65, 140, .25)",
            "text": "#24143f",
            "muted": "#6b587f",
            "cyan": "#7c3aed",
            "green": "#0d9488",
            "amber": "#b7791f",
            "coral": "#dc4c64",
            "app_bg": "radial-gradient(circle at 14% 6%, rgba(124,58,237,.12), transparent 27%), radial-gradient(circle at 86% 12%, rgba(196,181,253,.20), transparent 25%), linear-gradient(135deg, #ffffff 0%, #fbfaff 52%, #f3edff 100%)",
            "sidebar_bg": "rgba(255, 255, 255, .96)",
            "topbar_bg": "rgba(255, 255, 255, .90)",
            "card_bg": "rgba(124, 58, 237, .045)",
            "card_bg_strong": "rgba(255, 255, 255, .78)",
            "path_bg": "rgba(124, 58, 237, .055)",
            "path_text": "#3f2464",
            "chip_text": "#3f2464",
            "text_body": "#23113a",
            "code_text": "#3f2a5f",
            "shadow": "0 22px 58px rgba(74, 48, 126, .12)",
            "missing_bg": "rgba(220, 76, 100, .055)",
            "input_bg": "rgba(255, 255, 255, .86)",
            "container_bg": "rgba(255,255,255,.72)",
            "body_font": '"Comic Sans MS", "Comic Neue", "Trebuchet MS", ui-sans-serif, system-ui, sans-serif',
            "display_font": '"Comic Sans MS", "Comic Neue", "Trebuchet MS", ui-sans-serif, system-ui, sans-serif',
        }
    return {
        "scheme": "dark",
        "bg": "#080b0f",
        "panel": "#11161b",
        "panel2": "#171d23",
        "line": "rgba(255,255,255,.10)",
        "line_strong": "rgba(255,255,255,.18)",
        "text": "#edf2f4",
        "muted": "#8e9aa5",
        "cyan": "#53d7e8",
        "green": "#72e3a1",
        "amber": "#f2c46d",
        "coral": "#ff7b6f",
        "app_bg": "radial-gradient(circle at 12% 8%, rgba(83,215,232,.14), transparent 28%), radial-gradient(circle at 86% 12%, rgba(242,196,109,.09), transparent 24%), linear-gradient(135deg, #080a0d 0%, #11161b 48%, #090d11 100%)",
        "sidebar_bg": "rgba(12, 16, 20, .94)",
        "topbar_bg": "rgba(15, 19, 23, .88)",
        "card_bg": "rgba(255,255,255,.045)",
        "card_bg_strong": "rgba(15,19,23,.72)",
        "path_bg": "rgba(255,255,255,.035)",
        "path_text": "#cdd7dc",
        "chip_text": "#c7d0d6",
        "text_body": "#e6ecef",
        "code_text": "#d8e5e9",
        "shadow": "0 24px 70px rgba(0,0,0,.28)",
        "missing_bg": "rgba(255,123,111,.06)",
        "input_bg": "rgba(255,255,255,.045)",
        "container_bg": "rgba(15,19,23,.72)",
        "body_font": 'Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
        "display_font": 'Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
    }


CSS_TEMPLATE = """
<style>
:root {
  color-scheme: __scheme__;
  --bg: __bg__;
  --panel: __panel__;
  --panel-2: __panel2__;
  --line: __line__;
  --line-strong: __line_strong__;
  --text: __text__;
  --muted: __muted__;
  --cyan: __cyan__;
  --green: __green__;
  --amber: __amber__;
  --coral: __coral__;
  --app-bg: __app_bg__;
  --sidebar-bg: __sidebar_bg__;
  --topbar-bg: __topbar_bg__;
  --card-bg: __card_bg__;
  --card-bg-strong: __card_bg_strong__;
  --path-bg: __path_bg__;
  --path-text: __path_text__;
  --chip-text: __chip_text__;
  --text-body: __text_body__;
  --code-text: __code_text__;
  --app-shadow: __shadow__;
  --missing-bg: __missing_bg__;
  --input-bg: __input_bg__;
  --container-bg: __container_bg__;
  --body-font: __body_font__;
  --display-font: __display_font__;
}
.stApp {
  background: var(--app-bg);
  color: var(--text);
  font-family: var(--body-font);
}
[data-testid="stHeader"] {
  background: transparent;
}
[data-testid="stSidebar"] {
  background: var(--sidebar-bg);
  border-right: 1px solid var(--line);
  color: var(--text);
  font-family: var(--body-font);
}
.block-container {
  max-width: none;
  padding-top: 1.2rem;
  padding-bottom: 3rem;
}
h1, h2, h3 {
  letter-spacing: 0;
  color: var(--text);
  font-family: var(--display-font);
}
code {
  color: var(--code-text);
}
.stMarkdown,
.stMarkdown p,
[data-testid="stMarkdownContainer"],
[data-testid="stMarkdownContainer"] p,
[data-testid="stWidgetLabel"],
[data-testid="stWidgetLabel"] p,
[data-testid="stCaptionContainer"],
[data-testid="stCaptionContainer"] p,
.stTabs [role="tab"] {
  color: var(--text);
  font-family: var(--body-font);
}
[data-testid="stCaptionContainer"],
[data-testid="stCaptionContainer"] p {
  color: var(--muted);
}
.ui-icon {
  display: block;
}
.sidebar-title {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 4px 0 18px;
  color: var(--text);
  font-size: 20px;
  font-weight: 760;
  font-family: var(--display-font);
}
.sidebar-title .ui-icon {
  color: var(--cyan);
}
.app-topbar {
  border: 1px solid var(--line-strong);
  background: var(--topbar-bg);
  border-radius: 12px;
  padding: 16px 18px;
  margin-bottom: 18px;
  box-shadow: var(--app-shadow);
  backdrop-filter: blur(18px);
}
.app-title {
  display: flex;
  gap: 12px;
  align-items: center;
  font-weight: 720;
  font-size: 18px;
  font-family: var(--display-font);
}
.brand-mark {
  width: 36px;
  height: 36px;
  display: inline-grid;
  place-items: center;
  border-radius: 10px;
  background: linear-gradient(135deg, color-mix(in srgb, var(--cyan) 22%, transparent), color-mix(in srgb, var(--green) 15%, transparent));
  border: 1px solid color-mix(in srgb, var(--cyan) 45%, transparent);
  color: var(--cyan);
}
.brand-mark .ui-icon {
  width: 20px;
  height: 20px;
}
.path-line {
  margin-top: 10px;
  padding: 10px 12px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--path-bg);
  color: var(--path-text);
  font-family: SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.metric-row {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 16px;
}
.metric-card {
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 13px 14px;
  background: var(--card-bg);
}
.metric-card span {
  color: var(--muted);
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  font-family: var(--display-font);
}
.metric-card strong {
  display: block;
  margin-top: 5px;
  font-size: 20px;
  color: var(--text);
  font-family: var(--display-font);
}
.sample-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 8px 0 18px;
}
.meta-chip {
  border: 1px solid var(--line);
  border-radius: 999px;
  padding: 6px 9px;
  background: var(--card-bg);
  color: var(--chip-text);
  font-size: 12px;
}
.meta-chip b {
  color: var(--muted);
  font-weight: 700;
}
.block-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  border-bottom: 1px solid var(--line);
  padding-bottom: 10px;
  margin-bottom: 14px;
}
.block-title {
  display: flex;
  align-items: center;
  gap: 9px;
  min-width: 0;
}
.kind-badge {
  width: 26px;
  height: 26px;
  display: inline-grid;
  place-items: center;
  border-radius: 8px;
  border: 1px solid color-mix(in srgb, var(--cyan) 42%, transparent);
  color: var(--cyan);
  background: color-mix(in srgb, var(--cyan) 9%, transparent);
  font-size: 12px;
  font-weight: 800;
}
.kind-badge .ui-icon {
  width: 15px;
  height: 15px;
}
.kind-badge.missing {
  border-color: color-mix(in srgb, var(--coral) 45%, transparent);
  color: var(--coral);
  background: color-mix(in srgb, var(--coral) 9%, transparent);
}
.block-title strong {
  font-size: 13px;
  letter-spacing: .05em;
  text-transform: uppercase;
  color: var(--text);
  font-family: var(--display-font);
}
.role-pill {
  border: 1px solid var(--line-strong);
  border-radius: 999px;
  padding: 4px 8px;
  color: var(--chip-text);
  background: var(--card-bg);
  font-size: 11px;
}
.json-path {
  color: var(--muted);
  font-family: SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 11px;
  text-align: right;
  word-break: break-all;
}
.text-body {
  color: var(--text-body);
  font-size: 16px;
  line-height: 1.75;
  white-space: pre-wrap;
  font-family: var(--body-font);
}
.image-frame {
  width: fit-content;
  max-width: 100%;
}
.image-frame img {
  border-radius: 10px;
  border: 1px solid var(--line);
}
.image-note {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-top: 10px;
  color: var(--muted);
  font-family: SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 12px;
}
.status-pill {
  border-radius: 999px;
  padding: 4px 9px;
  font-family: var(--display-font);
  font-size: 11px;
  font-weight: 750;
}
.status-loaded {
  border: 1px solid rgba(114,227,161,.45);
  color: var(--green);
  background: rgba(114,227,161,.09);
}
.status-missing {
  border: 1px solid rgba(255,123,111,.45);
  color: var(--coral);
  background: rgba(255,123,111,.09);
}
.missing-box {
  min-height: 230px;
  display: grid;
  place-items: center;
  border: 1px dashed rgba(255,123,111,.45);
  border-radius: 12px;
  background:
    repeating-linear-gradient(135deg, rgba(255,255,255,.035) 0 10px, transparent 10px 22px),
    var(--missing-bg);
}
.missing-inner {
  text-align: center;
  max-width: 620px;
  padding: 22px;
}
.missing-icon {
  width: 72px;
  height: 72px;
  margin: 0 auto 14px;
  border: 2px solid rgba(255,123,111,.72);
  border-radius: 18px;
  position: relative;
}
.missing-icon:before,
.missing-icon:after {
  content: "";
  position: absolute;
  top: 33px;
  left: 13px;
  width: 46px;
  height: 3px;
  background: rgba(255,123,111,.88);
}
.missing-icon:before {
  transform: rotate(45deg);
}
.missing-icon:after {
  transform: rotate(-45deg);
}
.missing-inner strong {
  color: var(--coral);
  font-size: 16px;
}
.missing-inner code {
  display: block;
  margin-top: 10px;
  color: var(--code-text);
  white-space: normal;
  word-break: break-all;
}
.anchor-card {
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--card-bg);
  padding: 11px 12px;
  margin-bottom: 9px;
}
.anchor-card b {
  display: block;
  font-size: 13px;
}
.anchor-card code {
  display: block;
  margin-top: 4px;
  color: var(--muted);
  font-size: 10px;
  white-space: normal;
}
.anchor-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 999px;
  margin-right: 7px;
  background: var(--green);
}
.anchor-dot.missing {
  background: var(--coral);
}
.small-muted {
  color: var(--muted);
  font-size: 12px;
}
div[data-testid="stVerticalBlockBorderWrapper"] {
  border-color: rgba(255,255,255,.12);
  background: var(--container-bg);
}
.stTextInput input,
.stNumberInput input,
.stSelectbox div[data-baseweb="select"] > div {
  background: var(--input-bg);
  color: var(--text);
  border-color: var(--line);
  font-family: var(--body-font);
}
.stButton button,
.stDownloadButton button {
  border-radius: 8px;
  border-color: var(--line-strong);
  color: var(--text);
  font-family: var(--display-font);
  font-weight: 700;
}
.stButton button[kind="primary"] {
  background: var(--cyan);
  border-color: var(--cyan);
  color: white;
}
</style>
"""


def install_css(theme: str) -> None:
    css = CSS_TEMPLATE
    for key, value in theme_vars(theme).items():
        css = css.replace(f"__{key}__", value)
    st.markdown(css, unsafe_allow_html=True)
