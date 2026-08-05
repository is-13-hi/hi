# -*- coding: utf-8 -*-
"""
スマホ・PCで撮った写真や資料が、家庭内ネットワークを通って
プリンタから印刷されるまでの流れを、高校生向けに可視化する授業用アプリ。
"""

import time
import pandas as pd
import streamlit as st

# ----------------------------------------------------------------------
# ページ設定
# ----------------------------------------------------------------------
st.set_page_config(
    page_title="おうちネットワーク探検隊 〜写真が印刷されるまで〜",
    page_icon="🖨️",
    layout="centered",
)

st.markdown(
    """
    <style>
    .block-container { padding-top: 1.5rem; padding-bottom: 3rem; max-width: 900px; }
    .step-box {
        background-color: #EEF6FF; border-left: 6px solid #2E86DE;
        padding: 0.8rem 1rem; border-radius: 8px; font-size: 1.05rem; margin-bottom: 0.6rem;
    }
    .done-box {
        background-color: #EAFBEF; border-left: 6px solid #27AE60;
        padding: 1rem; border-radius: 8px; font-size: 1.15rem; text-align: center; font-weight: 600;
    }
    .ip-header {
        background-color: #2C3E50; color: #F2F4F6; border-radius: 10px;
        padding: 0.9rem 1.1rem; font-family: monospace; font-size: 1.05rem;
        display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;
    }
    .ip-header b { color: #FFD166; }
    .packet-card {
        background-color: #1E1E2E; color: #E6E6EF; border-radius: 10px;
        padding: 1rem; font-family: monospace; font-size: 0.95rem; line-height: 1.7;
    }
    .packet-card .k { color: #7FDBFF; }
    .packet-card .v { color: #FFD166; font-weight: bold; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ----------------------------------------------------------------------
# 機器データ
# ----------------------------------------------------------------------
DEVICES = {
    "phone": {
        "label": "スマホ", "icon": "📱", "ip": "192.168.1.10", "pos": (90, 90),
        "desc": "写真を撮ったり、印刷の操作をしたりする端末です。Wi-Fiでルーターにつながっています。",
    },
    "pc": {
        "label": "PC", "icon": "💻", "ip": "192.168.1.11", "pos": (90, 410),
        "desc": "有線LANケーブルでルーターに直接つながっている端末です。",
    },
    "router": {
        "label": "ルーター", "icon": "📡", "ip": "192.168.1.1", "pos": (370, 250),
        "desc": "家の中のデータの行き先を決める「司令塔」です。ルーティングテーブルを見て、次にどこへ送るかを判断します。",
    },
    "repeater": {
        "label": "中継器", "icon": "🔁", "ip": "192.168.1.2", "pos": (610, 250),
        "desc": "ルーターの電波が届きにくい場所まで、Wi-Fi信号を中継してくれる機器です。",
    },
    "printer": {
        "label": "プリンタ", "icon": "🖨️", "ip": "192.168.1.20", "pos": (760, 410),
        "desc": "送られてきたデータを受け取り、紙に印刷する機器です。",
    },
}

EDGES = [
    ("phone", "router", "Wi-Fi"),
    ("pc", "router", "有線LAN"),
    ("router", "repeater", "Wi-Fi（バックホール）"),
    ("repeater", "printer", "Wi-Fi"),
]

ROUTING_TABLE = pd.DataFrame([
    {"宛先ネットワーク": "192.168.1.10（スマホ）", "ネクストホップ": "直接接続", "インターフェース": "Wi-Fi"},
    {"宛先ネットワーク": "192.168.1.11（PC）", "ネクストホップ": "直接接続", "インターフェース": "有線LAN"},
    {"宛先ネットワーク": "192.168.1.20（プリンタ）", "ネクストホップ": "192.168.1.2（中継器）", "インターフェース": "Wi-Fi（バックホール）"},
])

CONTENT_OPTIONS = {"📷 写真データ": "📷", "📄 資料データ(PDF)": "📄"}
START_TTL = 64

# ----------------------------------------------------------------------
# SVG 描画ヘルパー
# ----------------------------------------------------------------------
def edge_key(a, b):
    return tuple(sorted((a, b)))


def build_svg(path_nodes, active_index, progress, packet_icon="📦"):
    completed_pairs = set()
    if active_index is not None:
        for i in range(active_index):
            completed_pairs.add(edge_key(path_nodes[i], path_nodes[i + 1]))
    active_pair = None
    if active_index is not None and active_index < len(path_nodes) - 1:
        active_pair = edge_key(path_nodes[active_index], path_nodes[active_index + 1])

    parts = ['<svg viewBox="0 0 850 480" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto;">']

    for a, b, kind in EDGES:
        x1, y1 = DEVICES[a]["pos"]
        x2, y2 = DEVICES[b]["pos"]
        key = edge_key(a, b)
        if key == active_pair:
            color, width = "#2E86DE", 6
        elif key in completed_pairs:
            color, width = "#27AE60", 6
        else:
            color, width = "#B9C2CC", 4
        dash = "" if (key == active_pair or key in completed_pairs) else 'stroke-dasharray="6,6"'
        parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
            f'stroke-width="{width}" {dash} stroke-linecap="round" />'
        )
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2 - 12
        parts.append(
            f'<text x="{mx}" y="{my}" font-size="15" fill="#5A6472" '
            f'text-anchor="middle" font-family="sans-serif">{kind}</text>'
        )

    if active_pair is not None:
        a, b = path_nodes[active_index], path_nodes[active_index + 1]
        x1, y1 = DEVICES[a]["pos"]
        x2, y2 = DEVICES[b]["pos"]
        px = x1 + (x2 - x1) * progress
        py = y1 + (y2 - y1) * progress
        parts.append(f'<circle cx="{px}" cy="{py}" r="18" fill="#FFD54F" stroke="#F39C12" stroke-width="3" />')
        parts.append(
            f'<text x="{px}" y="{py + 7}" font-size="18" text-anchor="middle" font-family="sans-serif">{packet_icon}</text>'
        )

    for key, dev in DEVICES.items():
        x, y = dev["pos"]
        in_path = key in path_nodes
        ring_color = "#2E86DE" if in_path else "#D0D5DB"
        parts.append(f'<circle cx="{x}" cy="{y}" r="42" fill="white" stroke="{ring_color}" stroke-width="4" />')
        parts.append(
            f'<text x="{x}" y="{y + 12}" font-size="34" text-anchor="middle" font-family="sans-serif">{dev["icon"]}</text>'
        )
        parts.append(
            f'<text x="{x}" y="{y + 65}" font-size="17" font-weight="bold" text-anchor="middle" '
            f'fill="#2C3E50" font-family="sans-serif">{dev["label"]}</text>'
        )
        parts.append(
            f'<text x="{x}" y="{y + 85}" font-size="14" font-weight="bold" text-anchor="middle" fill="#2E86DE" '
            f'font-family="monospace">{dev["ip"]}</text>'
        )

    parts.append("</svg>")
    return "".join(parts)


def highlighted_table(highlight_dest_substring=None):
    def _row_style(row):
        if highlight_dest_substring and highlight_dest_substring in row["宛先ネットワーク"]:
            return ["background-color: #FFF3B0; font-weight: bold;"] * len(row)
        return [""] * len(row)

    return ROUTING_TABLE.style.apply(_row_style, axis=1)


def render_packet_card(node_label, node_ip, src_ip, dst_ip, hop, total_hops, ttl, progress_pct, content_icon):
    return f"""
    <div class="packet-card">
    📦 <b>パケット情報</b>（ネットワーク機器が実際にやり取りする荷札のイメージ）<br>
    <span class="k">送信データ　　:</span> <span class="v">{content_icon}</span><br>
    <span class="k">送信元IP　　　:</span> <span class="v">{src_ip}</span><br>
    <span class="k">宛先IP　　　　:</span> <span class="v">{dst_ip}</span><br>
    <span class="k">現在地　　　　:</span> <span class="v">{node_label}（{node_ip}）</span><br>
    <span class="k">TTL（残り経由数）:</span> <span class="v">{ttl}</span><br>
    <span class="k">ホップ数　　　:</span> <span class="v">{hop} / {total_hops}</span><br>
    <span class="k">進行度　　　　:</span> <span class="v">{progress_pct}%</span>
    </div>
    """


# ----------------------------------------------------------------------
# ヘッダー
# ----------------------------------------------------------------------
st.title("🖨️ おうちネットワーク探検隊")
st.markdown(
    "スマホやPCから送った写真・資料が、どんな道すじを通ってプリンタから紙になって出てくるのか、"
    "**ネットワークマップ**の上で確認してみよう。"
)

with st.expander("📘 このアプリの使い方・用語解説"):
    st.markdown(
        "- **IPアドレス**：ネットワーク上の機器一人ひとりの「住所」のようなもの。\n"
        "- **ルーター**：どの機器にデータを送ればよいか判断する「郵便局の仕分け係」。\n"
        "- **中継器（Wi-Fi中継機）**：電波が届きにくい部屋まで、信号をリレーしてくれる係。\n"
        "- **ルーティングテーブル**：ルーターが持っている「宛先ごとの配送先リスト」。\n"
        "- **パケット**：データを送るときに分割された小さな荷物のかたまり。\n"
        "- **TTL**：パケットが経由できる残り回数。機器を1つ通るごとに1ずつ減っていきます。"
    )

st.divider()

# ----------------------------------------------------------------------
# ① 送信元・送るデータの選択
# ----------------------------------------------------------------------
st.subheader("① 送信元と送るデータを選ぼう")

col_a, col_b = st.columns(2)
with col_a:
    source_label = st.radio(
        "どちらの端末から送りますか？",
        options=["📱 スマホから送る", "💻 PCから送る"],
    )
with col_b:
    content_label = st.radio(
        "何を送りますか？",
        options=list(CONTENT_OPTIONS.keys()),
    )

source_key = "phone" if "スマホ" in source_label else "pc"
content_icon = CONTENT_OPTIONS[content_label]
path_nodes = [source_key, "router", "repeater", "printer"]
src_ip = DEVICES[source_key]["ip"]
dst_ip = DEVICES["printer"]["ip"]
n_steps = len(path_nodes) - 1

# 送信元が変わったらアニメーション状態をリセット
if st.session_state.get("cur_source") != source_key:
    st.session_state["cur_source"] = source_key
    st.session_state["step_idx"] = 0

st.markdown(
    f"""<div class="ip-header">
    <div>{DEVICES[source_key]['icon']} <b>送信元IP</b>：{src_ip}</div>
    <div style="font-size:1.4rem;">➡</div>
    <div>{DEVICES['printer']['icon']} <b>宛先IP</b>：{dst_ip}</div>
    </div>""",
    unsafe_allow_html=True,
)

st.divider()

with st.expander("🔍 各機器の役割をもっと詳しく"):
    for key, dev in DEVICES.items():
        st.markdown(f"**{dev['icon']} {dev['label']}**（{dev['ip']}）：{dev['desc']}")

st.divider()

# ----------------------------------------------------------------------
# ② ネットワークマップ ＋ 操作パネル
# ----------------------------------------------------------------------
st.subheader("② ネットワークマップを見ながら送ってみよう")

svg_placeholder = st.empty()
status_placeholder = st.empty()

mode = st.radio(
    "体験のしかたを選ぼう",
    ["🕹️ 自分でステップを進める（体験モード）", "▶️ 自動でアニメーション再生"],
    horizontal=True,
)

result_placeholder = st.empty()

if "step_idx" not in st.session_state:
    st.session_state["step_idx"] = 0

# --- 操作ボタン ---
if mode.startswith("🕹️"):
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔄 最初からやり直す", use_container_width=True):
            st.session_state["step_idx"] = 0
    with c2:
        next_disabled = st.session_state["step_idx"] >= n_steps
        if st.button("➡ 次のホップへ進む", type="primary", use_container_width=True, disabled=next_disabled):
            st.session_state["step_idx"] += 1
    auto_clicked = False
else:
    auto_clicked = st.button("🖨️ 印刷する（自動再生）", type="primary", use_container_width=True)

st.divider()

# ----------------------------------------------------------------------
# ③ ルーティングテーブル
# ----------------------------------------------------------------------
st.subheader("③ ルーターのルーティングテーブル")
st.caption("ルーターは、この表を見て「次にどこへデータを転送すればよいか」を判断しています。")
table_placeholder = st.empty()

st.divider()

# ----------------------------------------------------------------------
# ④ パケット情報パネル
# ----------------------------------------------------------------------
st.subheader("④ パケットの中身をのぞいてみよう")
packet_placeholder = st.empty()

STEP_MESSAGES = {
    ("phone", "router"): "📱 スマホがWi-Fiでルーターにデータを送信しています…",
    ("pc", "router"): "💻 PCが有線LANでルーターにデータを送信しています…",
    ("router", "repeater"): "🔁 ルーターが中継器へデータを転送しています…",
    ("repeater", "printer"): "🖨️ 中継器からプリンタへデータが届こうとしています…",
}


def draw_state(active_index, progress, table_highlight=None):
    svg_placeholder.markdown(build_svg(path_nodes, active_index, progress, content_icon), unsafe_allow_html=True)
    table_placeholder.dataframe(highlighted_table(table_highlight), use_container_width=True, hide_index=True)

    if active_index is None:
        node_label, node_ip, hop, ttl = DEVICES[source_key]["label"], src_ip, 0, START_TTL
        pct = 0
    elif active_index >= n_steps:
        node_label, node_ip = DEVICES["printer"]["label"], dst_ip
        hop, ttl, pct = n_steps, START_TTL - n_steps, 100
    else:
        a, b = path_nodes[active_index], path_nodes[active_index + 1]
        cur_node = a if progress < 1.0 else b
        node_label, node_ip = DEVICES[cur_node]["label"], DEVICES[cur_node]["ip"]
        hop = active_index if progress < 1.0 else active_index + 1
        ttl = START_TTL - hop
        pct = int(((active_index + progress) / n_steps) * 100)

    packet_placeholder.markdown(
        render_packet_card(node_label, node_ip, src_ip, dst_ip, hop, n_steps, ttl, pct, content_icon),
        unsafe_allow_html=True,
    )


# ----------------------------------------------------------------------
# 手動ステップモードの描画
# ----------------------------------------------------------------------
if mode.startswith("🕹️"):
    step = st.session_state["step_idx"]
    if step == 0:
        draw_state(None, 0.0)
        status_placeholder.info("「➡ 次のホップへ進む」を押すたびに、データが1つずつ機器を経由していきます。")
    elif step <= n_steps:
        cur_node = path_nodes[step - 1]
        nxt_node = path_nodes[step]
        highlight = "プリンタ" if cur_node == "router" else None
        draw_state(step - 1, 1.0, table_highlight=highlight)
        msg = STEP_MESSAGES.get((cur_node, nxt_node), f"{cur_node} から {nxt_node} へ送信中…")
        status_placeholder.markdown(f"<div class='step-box'>{msg}　→　{DEVICES[nxt_node]['label']}に到着</div>", unsafe_allow_html=True)
    if step >= n_steps:
        result_placeholder.markdown(
            "<div class='done-box'>✅ 印刷完了！プリンタから紙が出てきました 🖨️📄</div>",
            unsafe_allow_html=True,
        )

# ----------------------------------------------------------------------
# 自動再生モードの描画
# ----------------------------------------------------------------------
else:
    if not auto_clicked:
        draw_state(None, 0.0)
        status_placeholder.info("「🖨️ 印刷する」を押すと、データが通るルートが自動でアニメーション表示されます。")
    else:
        result_placeholder.empty()
        SEGMENT_SECONDS = 2.0
        FRAMES = 50
        for i in range(n_steps):
            cur_node = path_nodes[i]
            if cur_node == "router":
                status_placeholder.markdown(
                    "<div class='step-box'>📡 ルーターがルーティングテーブルを確認し、"
                    "宛先（プリンタ）への次の転送先を調べています…</div>",
                    unsafe_allow_html=True,
                )
                draw_state(i, 0.0, table_highlight="プリンタ")
                time.sleep(1.1)

            nxt_node = path_nodes[i + 1]
            msg = STEP_MESSAGES.get((cur_node, nxt_node), f"{cur_node} から {nxt_node} へ送信中…")
            status_placeholder.markdown(f"<div class='step-box'>{msg}</div>", unsafe_allow_html=True)

            for f in range(FRAMES + 1):
                draw_state(i, f / FRAMES)
                time.sleep(SEGMENT_SECONDS / FRAMES)

        draw_state(n_steps, 0.0)
        status_placeholder.empty()
        result_placeholder.markdown(
            "<div class='done-box'>✅ 印刷完了！プリンタから紙が出てきました 🖨️📄</div>",
            unsafe_allow_html=True,
        )
        st.balloons()

st.divider()
st.caption(
    "💡 授業メモ：緑色の線は「通過済みの区間」、青色の線は「今まさにデータが通っている区間」を表しています。"
    "パケット情報パネルのTTLは、機器を1つ経由するごとに1ずつ減っていく様子を表しています。"
)