import streamlit as st
import pandas as pd
from datetime import datetime

# --- ページ設定 ---
st.set_page_config(page_title="作業日報システム", layout="centered")

# --- セッション状態の初期化 ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'factory' not in st.session_state:
    st.session_state['factory'] = ""
if 'work_status' not in st.session_state:
    st.session_state['work_status'] = "before_start" # 状態管理用

# ==========================================
# 画面1: ログイン画面 (工場選択・別パスワード)
# ==========================================
def login_page():
    st.markdown("## 🏭 作業日報システム")
    
    with st.container(border=True):
        st.subheader("ログイン")
        
        # 工場の選択
        factory = st.selectbox("工場を選択してください", ["本社工場", "八尾工場"])
        
        # パスワード入力
        password = st.text_input("パスワード", type="password")
        
        if st.button("ログイン", type="primary", use_container_width=True):
            # --- パスワード判定ロジック ---
            # 本社工場なら 'honsha'、八尾工場なら 'yao' が正解とします
            if factory == "本社工場" and password == "honsha":
                st.session_state['logged_in'] = True
                st.session_state['factory'] = factory
                st.rerun()
            elif factory == "八尾工場" and password == "yao":
                st.session_state['logged_in'] = True
                st.session_state['factory'] = factory
                st.rerun()
            else:
                st.error("パスワードが違います")

# ==========================================
# 画面2: 作業日報入力画面 (画像を再現)
# ==========================================
def work_log_page():
    # サイドバー（ログアウト用）
    with st.sidebar:
        st.write(f"所属: **{st.session_state['factory']}**")
        st.write(f"担当: ゲスト ユーザー")
        if st.button("ログアウト"):
            st.session_state['logged_in'] = False
            st.rerun()

    # --- ヘッダーエリア ---
    # 画像のようなオレンジの縦棒を入れるのはCSSが必要ですが、
    # Streamlit標準機能で似たレイアウトを作ります。
    
    # 1段目: ライン種別 | 作業者
    c1, c2 = st.columns(2)
    with c1:
        st.selectbox("▎ライン種別", ["外径ライン", "組み立てライン", "3号ライン"])
    with c2:
        st.selectbox("▎作業者", ["廣瀬", "青井", "門", "坂本"])

    # 2段目: 型番
    st.selectbox("▎型番", ["検索...", "UA25", "SN6311T071", "RNU205ETW2"])

    # 3段目: 製品種別 | 機械種別
    c3, c4 = st.columns(2)
    with c3:
        st.selectbox("▎製品種別", ["SHI", "韓国", "シリンドリカル"])
    with c4:
        st.selectbox("▎機械種別", ["センターレス1号機", "T11J", "韓国製品組立機 1号機"])

    st.markdown("---") # 区切り線

    # --- 開始ボタン (緑色の大きなボタンをイメージ) ---
    # type="primary" にすると強調色(赤やオレンジなど設定依存)になりますが、
    # ここでは「一番目立つボタン」として配置します。
    if st.button("開 始", type="primary", use_container_width=True):
        st.toast("作業を開始しました！ ⏱️")

    st.markdown("") # 余白

    # --- 段取りエリア ---
    st.markdown("##### ▎段取種別")
    
    # ラジオボタンを横並びにするには columns を使うか CSS ですが、
    # 簡易的に標準の radio で horizontal=True を使います
    dandori_type = st.radio("段取種別", ["大段取", "小段取"], horizontal=True, label_visibility="collapsed")
    
    st.caption("※段取り中は以下のボタンを押下してください。")
    if st.button("段取り", use_container_width=True):
        st.toast(f"「{dandori_type}」を記録しました")

    st.markdown("---")

    # --- 中断・再開エリア ---
    st.markdown("##### ▎中断内容")
    st.selectbox("中断内容", ["(選択なし)", "材料待ち", "機械トラブル", "休憩", "清掃"], label_visibility="collapsed")
    
    # 中断・再開ボタンを横並びに
    c_pause, c_resume = st.columns(2)
    with c_pause:
        if st.button("中 断", use_container_width=True):
            st.warning("作業を中断しました")
    with c_resume:
        if st.button("再 開", use_container_width=True):
            st.info("作業を再開しました")

    st.markdown("---")

    # --- 実績入力エリア ---
    # 研削
    c_k1, c_k2 = st.columns(2)
    with c_k1:
        st.number_input("▎研削 研磨数", min_value=0, step=1)
    with c_k2:
        st.number_input("▎研削 不良数", min_value=0, step=1)
    
    # ラバ研
    c_r1, c_r2 = st.columns(2)
    with c_r1:
        st.number_input("▎ラバ研 研磨数", min_value=0, step=1)
    with c_r2:
        st.number_input("▎ラバ研 不良数", min_value=0, step=1)

    # 備考
    st.text_area("▎備考", height=100)

    # --- 終了ボタン ---
    st.markdown("")
    if st.button("終 了", use_container_width=True):
        st.success("お疲れ様でした！日報を送信しました。")

# ==========================================
# メイン処理
# ==========================================
if st.session_state['logged_in']:
    work_log_page()
else:
    login_page()
