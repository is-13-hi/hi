# -*- coding: utf-8 -*-
"""
スマホ・PCから送った指示が、家庭内ネットワークを通って
プリンタや家電に届くまでの流れを、高校生向けに可視化する授業用アプリ。
"""

import time
import pandas as pd
import streamlit as st

# ----------------------------------------------------------------------
# ページ設定
# ----------------------------------------------------------------------
st.set_page_config(
    page_title="おうちネットワーク探検隊 〜指示が家電に届くまで〜",
    page_icon="📡",
    layout="centered",
)

st.markdown(
    """
    <style>
    .block-container { padding-top: 1.5rem; padding-bottom: 3rem; max-width: 950px; }
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
        padding: 0.9rem 1.1rem; font-family: monospace; font-size: 1.02rem;
        display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;
    }
    .ip-header b { color: #FFD166; }
    .packet-card {
        background-color: #1E1E2E; color: #E6E6EF; border-radius: 10px;
        padding: 1rem; font-family: monospace; font-size: 0.92rem; line-height: 1.7;
    }
    .packet-card .k { color: #7FDBFF; }
    .packet-card .v { color: #FFD166; font-weight: bold; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ----------------------------------------------------------------------
# 機器データ（座標はSVGの座標系: 0-1000 x 0-580）
# ----------------------------------------------------------------------
DEVICES = {
    # --- 送信元（4台） ---
    "phone1": {"label": "スマホ①", "icon": "📱", "ip": "192.168.1.10", "pos": (70, 40), "kind": "source",
               "desc": "Wi-Fiでルーターにつながっているスマートフォンです。"},
    "phone2": {"label": "スマホ②", "icon": "📱", "ip": "192.168.1.12", "pos": (70, 190), "kind": "source",
               "desc": "Wi-Fiでルーターにつながっているスマートフォンです。"},
    "phone3": {"label": "スマホ③", "icon": "📱", "ip": "192.168.1.13", "pos": (70, 340), "kind": "source",
               "desc": "Wi-Fiでルーターにつながっているスマートフォンです。"},
    "pc": {"label": "PC", "icon": "💻", "ip": "192.168.1.11", "pos": (70, 490), "kind": "source",
           "desc": "有線LANケーブルでルーターに直接つながっている端末です。"},
    # --- ネットワーク機器 ---
    "router": {"label": "ルーター", "icon": "📡", "ip": "192.168.1.1", "pos": (380, 265), "kind": "network",
               "desc": "家の中のデータの行き先を決める「司令塔」です。ルーティングテーブルを見て、次にどこへ送るかを判断します。"},
    "repeater": {"label": "中継器", "icon": "🔁", "ip": "192.168.1.2", "pos": (650, 265), "kind": "network",
                 "desc": "ルーターの電波が届きにくい場所まで、Wi-Fi信号を中継してくれる機器です。"},
    # --- ルーターに直結する送信先（2台） ---
    "tv": {"label": "テレビ", "icon": "📺", "ip": "192.168.1.30", "pos": (380, 40), "kind": "destination",
           "desc": "ルーターに直接Wi-Fiでつながっているテレビです。"},
    "light": {"label": "スマート照明", "icon": "💡", "ip": "192.168.1.31", "pos": (380, 490), "kind": "destination",
              "desc": "ルーターに直接Wi-Fiでつながっている照明です。"},
    # --- 中継器を経由する送信先（4台） ---
    "printer": {"label": "プリンタ", "icon": "🖨️", "ip": "192.168.1.20", "pos": (930, 40), "kind": "destination",
                "desc": "中継器を経由してつながっているプリンタです。"},
    "aircon": {"label": "エアコン", "icon": "❄️", "ip": "192.168.1.21", "pos": (930, 190), "kind": "destination",
               "desc": "中継器を経由してつながっているエアコンです。"},
    "washer": {"label": "洗濯機", "icon": "🌀", "ip": "192.168.1.22", "pos": (930, 340), "kind": "destination",
               "desc": "中継器を経由してつながっている洗濯機です。"},
    "robot_vacuum": {"label": "ロボット掃除機", "icon": "🧹", "ip": "192.168.1.23", "pos": (930, 490), "kind": "destination",
                      "desc": "中継器を経由してつながっているロボット掃除機です。"},
}

SOURCE_KEYS = ["phone1", "phone2", "phone3", "pc"]
DEST_KEYS = ["tv", "light", "printer", "aircon", "washer", "robot_vacuum"]
ROUTER_CANDIDATES = ["tv", "light", "repeater"]
REPEATER_CANDIDATES = ["printer", "aircon", "washer", "robot_vacuum"]

EDGES = [
    ("phone1", "router", "Wi-Fi"),
    ("phone2", "router", "Wi-Fi"),
    ("phone3", "router", "Wi-Fi"),
    ("pc", "router", "有線LAN"),
    ("router", "tv", "Wi-Fi"),
    ("router", "light", "Wi-Fi"),
    ("router", "repeater", "Wi-Fi（バックホール）"),
    ("repeater", "printer", "Wi-Fi"),
    ("repeater", "aircon", "Wi-Fi"),
    ("repeater", "washer", "Wi-Fi"),
    ("repeater", "robot_vacuum", "Wi-Fi"),
]

INSTRUCTIONS = {
    "tv": ["📺 電源を入れる", "🔀 チャンネルを変える"],
    "light": ["💡 電気をつける", "🌙 明るさを落とす"],
    "printer": ["🖨️ 写真を印刷する", "📄 資料を印刷する"],
    "aircon": ["❄️ 冷房をつける", "🌡️ 設定温度を下げる"],
    "washer": ["🌀 洗濯運転を開始する", "⏰ 予約運転にする"],
    "robot_vacuum": ["🧹 掃除を開始する", "🔋 充電ドックに戻る"],
}

START_TTL = 64


def edge_kind(a, b):
    for x, y, k in EDGES:
        if {x, y} == {a, b}:
            return k
    return ""


def resolve_true_path(source_key, dest_key):
    if dest_key in ("tv", "light"):
        return [source_key, "router", dest_key]
    return [source_key, "router", "repeater", dest_key]


def router_table_df():
    rows = []
    for key in DEST_KEYS:
        if key in ("tv", "light"):
            next_hop, iface = "直接接続", "Wi-Fi"
        else:
            next_hop, iface = "192.168.1.2（中継器）", "Wi-Fi（バックホール）"
        rows.append({
            "宛先機器": f"{DEVICES[key]['icon']} {DEVICES[key]['label']}",
            "宛先IP": DEVICES[key]["ip"],
            "ネクストホップ": next_hop,
            "インターフェース": iface,
        })
    return pd.DataFrame(rows)


def repeater_table_df():
    rows = []
    for key in REPEATER_CANDIDATES:
        rows.append({
            "宛先機器": f"{DEVICES[key]['icon']} {DEVICES[key]['label']}",
            "宛先IP": DEVICES[key]["ip"],
            "ネクストホップ": "直接接続",
            "インターフェース": "Wi-Fi",
        })
    return pd.DataFrame(rows)


def styled_table(df, highlight_ip=None):
    def _row_style(row):
        if highlight_ip and row["宛先IP"] == highlight_ip:
            return ["background-color: #FFF3B0; font-weight: bold;"] * len(row)
        return [""] * len(row)
    return df.style.apply(_row_style, axis=1)


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
    if active_index is not None and 0 <= active_index < len(path_nodes) - 1:
        active_pair = edge_key(path_nodes[active_index], path_nodes[active_index + 1])

    parts = ['<svg viewBox="0 0 1000 580" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto;">']

    for a, b, kind in EDGES:
        x1, y1 = DEVICES[a]["pos"]
        x2, y2 = DEVICES[b]["pos"]
        key = edge_key(a, b)
        if key == active_pair:
            color, width = "#2E86DE", 6
        elif key in completed_pairs:
            color, width = "#27AE60", 6
        else:
            color, width = "#C3CAD1", 3
        dash = "" if (key == active_pair or key in completed_pairs) else 'stroke-dasharray="5,6"'
        parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
            f'stroke-width="{width}" {dash} stroke-linecap="round" />'
        )

    if active_pair is not None:
        a, b = path_nodes[active_index], path_nodes[active_index + 1]
        x1, y1 = DEVICES[a]["pos"]
        x2, y2 = DEVICES[b]["pos"]
        px = x1 + (x2 - x1) * progress
        py = y1 + (y2 - y1) * progress
        parts.append(f'<circle cx="{px}" cy="{py}" r="16" fill="#FFD54F" stroke="#F39C12" stroke-width="3" />')
        parts.append(
            f'<text x="{px}" y="{py + 6}" font-size="16" text-anchor="middle" font-family="sans-serif">{packet_icon}</text>'
        )

    for key, dev in DEVICES.items():
        x, y = dev["pos"]
        in_path = key in path_nodes
        ring_color = "#2E86DE" if in_path else "#D0D5DB"
        parts.append(f'<circle cx="{x}" cy="{y}" r="32" fill="white" stroke="{ring_color}" stroke-width="4" />')
        parts.append(
            f'<text x="{x}" y="{y + 10}" font-size="26" text-anchor="middle" font-family="sans-serif">{dev["icon"]}</text>'
        )
        parts.append(
            f'<text x="{x}" y="{y + 50}" font-size="14" font-weight="bold" text-anchor="middle" '
            f'fill="#2C3E50" font-family="sans-serif">{dev["label"]}</text>'
        )
        parts.append(
            f'<text x="{x}" y="{y + 66}" font-size="12" font-weight="bold" text-anchor="middle" fill="#2E86DE" '
            f'font-family="monospace">{dev["ip"]}</text>'
        )

    parts.append("</svg>")
    return "".join(parts)


def render_packet_card(node_label, node_ip, src_ip, dst_ip, hop, total_hops, ttl, progress_pct, content_icon):
    return f"""
    <div class="packet-card">
    📦 <b>パケット情報</b>（ネットワーク機器が実際にやり取りする荷札のイメージ）<br>
    <span class="k">送る指示　　　:</span> <span class="v">{content_icon}</span><br>
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
st.title("📡 おうちネットワーク探検隊")
st.markdown(
    "スマホやPCから送った指示が、どんな道すじを通ってプリンタや家電に届くのか、"
    "**ネットワークマップ**の上で確認してみよう。"
)

with st.expander("📘 このアプリの使い方・用語解説"):
    st.markdown(
        "- **IPアドレス**：ネットワーク上の機器一人ひとりの「住所」のようなもの。\n"
        "- **ルーター**：どの機器にデータを送ればよいか判断する「郵便局の仕分け係」。\n"
        "- **中継器（Wi-Fi中継機）**：電波が届きにくい部屋まで、信号をリレーしてくれる係。\n"
        "- **ルーティングテーブル**：ルーターや中継器が持っている「宛先ごとの配送先リスト」。\n"
        "- **パケット**：データを送るときに分割された小さな荷物のかたまり。\n"
        "- **TTL**：パケットが経由できる残り回数。機器を1つ通るごとに1ずつ減っていきます。"
    )

st.divider()

# ----------------------------------------------------------------------
# ① 送信元・送信先・送る指示の選択
# ----------------------------------------------------------------------
st.subheader("① 送信元・送信先・送る指示を選ぼう")

col1, col2, col3 = st.columns(3)
with col1:
    src_choice = st.selectbox(
        "📤 送信元",
        SOURCE_KEYS,
        format_func=lambda k: f"{DEVICES[k]['icon']} {DEVICES[k]['label']}",
    )
with col2:
    dst_choice = st.selectbox(
        "📥 送信先",
        DEST_KEYS,
        format_func=lambda k: f"{DEVICES[k]['icon']} {DEVICES[k]['label']}",
    )
with col3:
    instruction = st.radio("📝 送る指示", INSTRUCTIONS[dst_choice], key=f"instr_{dst_choice}")

source_key = src_choice
dest_key = dst_choice
true_path = resolve_true_path(source_key, dest_key)
n_steps = len(true_path) - 1
src_ip = DEVICES[source_key]["ip"]
dst_ip = DEVICES[dest_key]["ip"]

# 送信元・送信先が変わったら体験モードの進行状況をリセット
if st.session_state.get("cur_pair") != (source_key, dest_key):
    st.session_state["cur_pair"] = (source_key, dest_key)
    st.session_state["exp_stage"] = "start"
    st.session_state["exp_path"] = [source_key]
    st.session_state["exp_feedback"] = None

st.markdown(
    f"""<div class="ip-header">
    <div>{DEVICES[source_key]['icon']} <b>送信元IP</b>：{src_ip}</div>
    <div style="font-size:1.4rem;">➡</div>
    <div>{DEVICES[dest_key]['icon']} <b>宛先IP</b>：{dst_ip}</div>
    </div>""",
    unsafe_allow_html=True,
)

st.divider()

with st.expander("🔍 各機器の役割をもっと詳しく"):
    st.markdown("**📤 送信元機器**")
    for key in SOURCE_KEYS:
        dev = DEVICES[key]
        st.markdown(f"- **{dev['icon']} {dev['label']}**（{dev['ip']}）：{dev['desc']}")
    st.markdown("**📶 ネットワーク機器**")
    for key in ("router", "repeater"):
        dev = DEVICES[key]
        st.markdown(f"- **{dev['icon']} {dev['label']}**（{dev['ip']}）：{dev['desc']}")
    st.markdown("**📥 送信先機器（家電）**")
    for key in DEST_KEYS:
        dev = DEVICES[key]
        st.markdown(f"- **{dev['icon']} {dev['label']}**（{dev['ip']}）：{dev['desc']}")

st.divider()

# ----------------------------------------------------------------------
# ② ネットワークマップ
# ----------------------------------------------------------------------
st.subheader("② ネットワークマップ")
svg_placeholder = st.empty()
status_placeholder = st.empty()

st.divider()

# ----------------------------------------------------------------------
# ③ ルーティングテーブル ＋ 操作パネル
# ----------------------------------------------------------------------
st.subheader("③ ルーティングテーブルを見て進めよう")

mode = st.radio(
    "体験のしかたを選ぼう",
    ["🕹️ 自分でルートを選んで進む（体験モード）", "▶️ 自動でアニメーション再生"],
    horizontal=True,
)

result_placeholder = st.empty()
feedback_placeholder = st.empty()
st.markdown("**📡 ルーターのルーティングテーブル**")
table_router_placeholder = st.empty()
st.markdown("**🔁 中継器のルーティングテーブル**")
table_repeater_placeholder = st.empty()
control_placeholder = st.container()

st.divider()

# ----------------------------------------------------------------------
# ④ パケット情報パネル
# ----------------------------------------------------------------------
st.subheader("④ パケットの中身をのぞいてみよう")
packet_placeholder = st.empty()


def draw_state(active_index, progress, highlight_ip=None, table_which=None):
    svg_placeholder.markdown(build_svg(true_path, active_index, progress, "📦"), unsafe_allow_html=True)

    table_router_placeholder.dataframe(
        styled_table(router_table_df(), highlight_ip if table_which == "router" else None),
        use_container_width=True, hide_index=True,
    )
    table_repeater_placeholder.dataframe(
        styled_table(repeater_table_df(), highlight_ip if table_which == "repeater" else None),
        use_container_width=True, hide_index=True,
    )

    if active_index is None:
        node_label, node_ip, hop, ttl, pct = DEVICES[source_key]["label"], src_ip, 0, START_TTL, 0
    elif active_index >= n_steps:
        node_label, node_ip = DEVICES[dest_key]["label"], dst_ip
        hop, ttl, pct = n_steps, START_TTL - n_steps, 100
    else:
        a, b = true_path[active_index], true_path[active_index + 1]
        cur_node = a if progress < 1.0 else b
        node_label, node_ip = DEVICES[cur_node]["label"], DEVICES[cur_node]["ip"]
        hop = active_index if progress < 1.0 else active_index + 1
        ttl = START_TTL - hop
        pct = int(((active_index + progress) / n_steps) * 100)

    packet_placeholder.markdown(
        render_packet_card(node_label, node_ip, src_ip, dst_ip, hop, n_steps, ttl, pct, instruction),
        unsafe_allow_html=True,
    )


def animate_edge(path_prefix, edge_index, seconds=1.3, frames=26):
    for f in range(frames + 1):
        draw_state(edge_index, f / frames)
        time.sleep(seconds / frames)


# ----------------------------------------------------------------------
# 🕹️ 体験モード：ルーティングテーブルを見てルートを自分で選ぶ
# ----------------------------------------------------------------------
if mode.startswith("🕹️"):
    stage = st.session_state["exp_stage"]
    path_so_far = st.session_state["exp_path"]

    if st.session_state["exp_feedback"]:
        kind, msg = st.session_state["exp_feedback"]
        (feedback_placeholder.success if kind == "success" else feedback_placeholder.error)(msg)

    if stage == "start":
        draw_state(None, 0.0)
        status_placeholder.info("「▶ 送信を開始する」を押すと、まずルーターにデータが届きます。")
        with control_placeholder:
            if st.button("▶ 送信を開始する", type="primary", use_container_width=True):
                start_msg = (
                    f"{DEVICES[source_key]['icon']} {DEVICES[source_key]['label']} からルーターへ、"
                    f"{edge_kind(source_key, 'router')}でデータが送られています…"
                )
                status_placeholder.markdown(f"<div class='step-box'>{start_msg}</div>", unsafe_allow_html=True)
                animate_edge(path_so_far, 0)
                path_so_far.append("router")
                st.session_state["exp_path"] = path_so_far
                st.session_state["exp_stage"] = "at_router"
                st.session_state["exp_feedback"] = ("success", f"✅ {DEVICES['router']['icon']} ルーターに届きました。次はどこへ転送するか、ルーティングテーブルを見て選ぼう。")
                draw_state(1, 0.0, highlight_ip=dst_ip, table_which="router")

    elif stage == "at_router":
        draw_state(0, 1.0, highlight_ip=dst_ip, table_which="router")
        status_placeholder.markdown(
            f"<div class='step-box'>📡 ルーターが「{DEVICES[dest_key]['icon']} {DEVICES[dest_key]['label']}（{dst_ip}）」宛のデータを受け取りました。"
            "ルーティングテーブルの<b>ネクストホップ</b>の列を見て、次にどこへ転送すればよいか選ぼう。</div>",
            unsafe_allow_html=True,
        )
        with control_placeholder:
            cols = st.columns(len(ROUTER_CANDIDATES))
            for col, cand in zip(cols, ROUTER_CANDIDATES):
                with col:
                    if st.button(f"{DEVICES[cand]['icon']} {DEVICES[cand]['label']}", key=f"router_{cand}", use_container_width=True):
                        correct = true_path[len(path_so_far)]
                        if cand == correct:
                            path_so_far.append(cand)
                            st.session_state["exp_path"] = path_so_far
                            animate_edge(path_so_far, len(path_so_far) - 2)
                            if cand == "repeater":
                                st.session_state["exp_stage"] = "at_repeater"
                                st.session_state["exp_feedback"] = ("success", "✅ 正解！中継器に転送されました。次は中継器の表を見て、最終的な機器を選ぼう。")
                            else:
                                st.session_state["exp_stage"] = "done"
                                st.session_state["exp_feedback"] = ("success", "🎉 正解！宛先の機器にデータが届きました。")
                        else:
                            st.session_state["exp_feedback"] = ("error", f"❌ ちがうよ。ルーティングテーブルで「{DEVICES[dest_key]['label']}（{dst_ip}）」の行の<b>ネクストホップ</b>をもう一度確認してみよう。")

    elif stage == "at_repeater":
        draw_state(1, 1.0, highlight_ip=dst_ip, table_which="repeater")
        status_placeholder.markdown(
            f"<div class='step-box'>🔁 中継器が「{DEVICES[dest_key]['icon']} {DEVICES[dest_key]['label']}（{dst_ip}）」宛のデータを受け取りました。"
            "中継器のルーティングテーブルを見て、どの機器に届ければよいか選ぼう。</div>",
            unsafe_allow_html=True,
        )
        with control_placeholder:
            cols = st.columns(len(REPEATER_CANDIDATES))
            for col, cand in zip(cols, REPEATER_CANDIDATES):
                with col:
                    if st.button(f"{DEVICES[cand]['icon']} {DEVICES[cand]['label']}", key=f"repeater_{cand}", use_container_width=True):
                        correct = true_path[len(path_so_far)]
                        if cand == correct:
                            path_so_far.append(cand)
                            st.session_state["exp_path"] = path_so_far
                            animate_edge(path_so_far, len(path_so_far) - 2)
                            st.session_state["exp_stage"] = "done"
                            st.session_state["exp_feedback"] = ("success", "🎉 正解！宛先の機器にデータが届きました。")
                        else:
                            st.session_state["exp_feedback"] = ("error", f"❌ ちがうよ。中継器のルーティングテーブルで「{DEVICES[dest_key]['label']}（{dst_ip}）」の行をもう一度確認してみよう。")

    if st.session_state["exp_stage"] == "done":
        draw_state(n_steps, 0.0)
        status_placeholder.empty()
        result_placeholder.markdown(
            f"<div class='done-box'>✅ 実行完了！{DEVICES[dest_key]['icon']} {DEVICES[dest_key]['label']}が「{instruction}」を実行しました 🎉</div>",
            unsafe_allow_html=True,
        )
        with control_placeholder:
            if st.button("🔄 最初からやり直す", use_container_width=True):
                st.session_state["exp_stage"] = "start"
                st.session_state["exp_path"] = [source_key]
                st.session_state["exp_feedback"] = None

# ----------------------------------------------------------------------
# ▶️ 自動再生モード
# ----------------------------------------------------------------------
else:
    table_router_placeholder.dataframe(styled_table(router_table_df()), use_container_width=True, hide_index=True)
    table_repeater_placeholder.dataframe(styled_table(repeater_table_df()), use_container_width=True, hide_index=True)

    with control_placeholder:
        auto_clicked = st.button("▶ 実行する（自動再生）", type="primary", use_container_width=True)

    if not auto_clicked:
        draw_state(None, 0.0)
        status_placeholder.info("「▶ 実行する」を押すと、データが通るルートが自動でアニメーション表示されます。")
    else:
        result_placeholder.empty()
        SEGMENT_SECONDS = 2.0
        FRAMES = 50
        for i in range(n_steps):
            cur_node, nxt_node = true_path[i], true_path[i + 1]
            if cur_node == "router":
                status_placeholder.markdown(
                    f"<div class='step-box'>📡 ルーターがルーティングテーブルを確認し、"
                    f"「{DEVICES[dest_key]['label']}」への次の転送先を調べています…</div>",
                    unsafe_allow_html=True,
                )
                draw_state(i, 0.0, highlight_ip=dst_ip, table_which="router")
                time.sleep(1.1)
            elif cur_node == "repeater":
                status_placeholder.markdown(
                    f"<div class='step-box'>🔁 中継器がルーティングテーブルを確認し、"
                    f"「{DEVICES[dest_key]['label']}」への転送先を調べています…</div>",
                    unsafe_allow_html=True,
                )
                draw_state(i, 0.0, highlight_ip=dst_ip, table_which="repeater")
                time.sleep(1.1)

            msg = f"{DEVICES[cur_node]['icon']} {DEVICES[cur_node]['label']} から {DEVICES[nxt_node]['icon']} {DEVICES[nxt_node]['label']} へ、{edge_kind(cur_node, nxt_node)}でデータが送られています…"
            status_placeholder.markdown(f"<div class='step-box'>{msg}</div>", unsafe_allow_html=True)

            for f in range(FRAMES + 1):
                draw_state(i, f / FRAMES)
                time.sleep(SEGMENT_SECONDS / FRAMES)

        draw_state(n_steps, 0.0)
        status_placeholder.empty()
        result_placeholder.markdown(
            f"<div class='done-box'>✅ 実行完了！{DEVICES[dest_key]['icon']} {DEVICES[dest_key]['label']}が「{instruction}」を実行しました 🎉</div>",
            unsafe_allow_html=True,
        )
        st.balloons()

st.divider()
st.caption(
    "💡 授業メモ：緑色の線は「通過済みの区間」、青色の線は「今まさにデータが通っている区間」を表しています。"
    "体験モードでは、ルーティングテーブルの<b>ネクストホップ</b>列を読み取って、正しい転送先を自分で選んでみよう。"
)