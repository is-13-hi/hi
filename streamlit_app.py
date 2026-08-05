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

# ----------------------------------------------------------------------
# スマホでも見やすくするための簡単なCSS調整
# ----------------------------------------------------------------------
st.markdown(
    """
    <style>
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 3rem;
        max-width: 900px;
    }
    .step-box {
        background-color: #EEF6FF;
        border-left: 6px solid #2E86DE;
        padding: 0.8rem 1rem;
        border-radius: 8px;
        font-size: 1.05rem;
        margin-bottom: 0.6rem;
    }
    .done-box {
        background-color: #EAFBEF;
        border-left: 6px solid #27AE60;
        padding: 1rem;
        border-radius: 8px;
        font-size: 1.15rem;
        text-align: center;
        font-weight: 600;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ----------------------------------------------------------------------
# 機器データ（座標はSVGの座標系: 0-850 x 0-480）
# ----------------------------------------------------------------------
DEVICES = {
    "phone": {
        "label": "スマホ", "icon": "📱", "ip": "192.168.1.10",
        "pos": (90, 90),
        "desc": "写真を撮ったり、印刷の操作をしたりする端末です。Wi-Fiでルーターにつながっています。",
    },
    "pc": {
        "label": "PC", "icon": "💻", "ip": "192.168.1.11",
        "pos": (90, 410),
        "desc": "有線LANケーブルでルーターに直接つながっている端末です。",
    },
    "router": {
        "label": "ルーター", "icon": "📡", "ip": "192.168.1.1",
        "pos": (370, 250),
        "desc": "家の中のデータの行き先を決める「司令塔」です。ルーティングテーブルを見て、次にどこへ送るかを判断します。",
    },
    "repeater": {
        "label": "中継器", "icon": "🔁", "ip": "192.168.1.2",
        "pos": (610, 250),
        "desc": "ルーターの電波が届きにくい場所まで、Wi-Fi信号を中継してくれる機器です。",
    },
    "printer": {
        "label": "プリンタ", "icon": "🖨️", "ip": "192.168.1.20",
        "pos": (760, 410),
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

# ----------------------------------------------------------------------
# SVG 描画ヘルパー
# ----------------------------------------------------------------------
def edge_key(a, b):
    return tuple(sorted((a, b)))


def build_svg(path_nodes, active_index, progress):
    """
    path_nodes: 送信経路のノード名リスト（例: ["phone","router","repeater","printer"]）
    active_index: 現在アニメーション中の区間インデックス（Noneなら未送信）
    progress: 0.0-1.0 現在区間内の進み具合
    """
    completed_pairs = set()
    if active_index is not None:
        for i in range(active_index):
            completed_pairs.add(edge_key(path_nodes[i], path_nodes[i + 1]))
    active_pair = None
    if active_index is not None and active_index < len(path_nodes) - 1:
        active_pair = edge_key(path_nodes[active_index], path_nodes[active_index + 1])

    parts = ['<svg viewBox="0 0 850 480" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto;">']

    # --- 背景の線（機器同士のつながり） ---
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

    # --- 移動中のパケット ---
    if active_pair is not None:
        a, b = path_nodes[active_index], path_nodes[active_index + 1]
        x1, y1 = DEVICES[a]["pos"]
        x2, y2 = DEVICES[b]["pos"]
        px = x1 + (x2 - x1) * progress
        py = y1 + (y2 - y1) * progress
        parts.append(f'<circle cx="{px}" cy="{py}" r="16" fill="#FFD54F" stroke="#F39C12" stroke-width="3" />')
        parts.append(
            f'<text x="{px}" y="{py + 6}" font-size="16" text-anchor="middle" font-family="sans-serif">📦</text>'
        )

    # --- 機器アイコン ---
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
            f'<text x="{x}" y="{y + 85}" font-size="13" text-anchor="middle" fill="#7F8C9A" '
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
        "- **パケット**：データを送るときに分割された小さな荷物のかたまり。"
    )

st.divider()

# ----------------------------------------------------------------------
# 送信元の選択
# ----------------------------------------------------------------------
st.subheader("① 送信元を選ぼう")
source_label = st.radio(
    "どちらの端末から印刷データを送りますか？",
    options=["📱 スマホから送る", "💻 PCから送る"],
    horizontal=True,
)
source_key = "phone" if "スマホ" in source_label else "pc"
path_nodes = [source_key, "router", "repeater", "printer"]

# ----------------------------------------------------------------------
# 機器の役割説明（折りたたみ）
# ----------------------------------------------------------------------
cols = st.columns(5)
for col, key in zip(cols, DEVICES.keys()):
    dev = DEVICES[key]
    with col:
        st.markdown(f"<div style='text-align:center;font-size:28px'>{dev['icon']}</div>", unsafe_allow_html=True)
        st.markdown(f"<div style='text-align:center;font-size:13px;font-weight:bold'>{dev['label']}</div>", unsafe_allow_html=True)
with st.expander("🔍 各機器の役割をもっと詳しく"):
    for key, dev in DEVICES.items():
        st.markdown(f"**{dev['icon']} {dev['label']}**（{dev['ip']}）：{dev['desc']}")

st.divider()

# ----------------------------------------------------------------------
# ネットワークマップ表示エリア
# ----------------------------------------------------------------------
st.subheader("② ネットワークマップ")
svg_placeholder = st.empty()
status_placeholder = st.empty()
svg_placeholder.markdown(build_svg(path_nodes, None, 0.0), unsafe_allow_html=True)
status_placeholder.info("下の「🖨️ 印刷する」ボタンを押すと、データが通るルートがアニメーションで表示されます。")

st.divider()

# ----------------------------------------------------------------------
# ルーティングテーブル表示エリア
# ----------------------------------------------------------------------
st.subheader("③ ルーターのルーティングテーブル")
st.caption("ルーターは、この表を見て「次にどこへデータを転送すればよいか」を判断しています。")
table_placeholder = st.empty()
table_placeholder.dataframe(highlighted_table(), use_container_width=True, hide_index=True)

st.divider()

# ----------------------------------------------------------------------
# 印刷ボタン & アニメーション
# ----------------------------------------------------------------------
st.subheader("④ 印刷してみよう")
result_placeholder = st.empty()

if st.button("🖨️ 印刷する", type="primary", use_container_width=True):
    result_placeholder.empty()

    step_messages = {
        ("phone", "router"): "📱 スマホがWi-Fiでルーターにデータを送信しています…",
        ("pc", "router"): "💻 PCが有線LANでルーターにデータを送信しています…",
        ("router", "repeater"): "🔁 ルーターが中継器へデータを転送しています…",
        ("repeater", "printer"): "🖨️ 中継器からプリンタへデータが届こうとしています…",
    }

    n_steps = len(path_nodes) - 1
    for i in range(n_steps):
        cur_node = path_nodes[i]

        # ルーターに到着したタイミングで、ルーティングテーブル参照の演出を挟む
        if cur_node == "router":
            status_placeholder.markdown(
                "<div class='step-box'>📡 ルーターがルーティングテーブルを確認し、"
                "宛先（プリンタ）への次の転送先を調べています…</div>",
                unsafe_allow_html=True,
            )
            table_placeholder.dataframe(
                highlighted_table("プリンタ"), use_container_width=True, hide_index=True
            )
            svg_placeholder.markdown(build_svg(path_nodes, i, 0.0), unsafe_allow_html=True)
            time.sleep(1.1)
            table_placeholder.dataframe(highlighted_table(), use_container_width=True, hide_index=True)

        nxt_node = path_nodes[i + 1]
        msg = step_messages.get((cur_node, nxt_node), f"{cur_node} から {nxt_node} へ送信中…")
        status_placeholder.markdown(f"<div class='step-box'>{msg}</div>", unsafe_allow_html=True)

        for p in range(0, 101, 5):
            svg_placeholder.markdown(build_svg(path_nodes, i, p / 100), unsafe_allow_html=True)
            time.sleep(0.02)

    svg_placeholder.markdown(build_svg(path_nodes, n_steps, 0.0), unsafe_allow_html=True)
    status_placeholder.empty()
    result_placeholder.markdown(
        "<div class='done-box'>✅ 印刷完了！プリンタから紙が出てきました 🖨️📄</div>",
        unsafe_allow_html=True,
    )
    st.balloons()

st.divider()
st.caption(
    "💡 授業メモ：ルート上の緑色の線は「通過済みの区間」、青色の線は「今まさにデータが通っている区間」を表しています。"
)