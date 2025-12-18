import streamlit as st
import pandas as pd
from datetime import datetime, date

# --- ページ設定 (ブラウザのタブ名など) ---
st.set_page_config(
    page_title="Daily Walker",
    page_icon="🚶",
    layout="centered" # スマホでも見やすいように中央寄せ
)

# --- 擬似的なデータベース (後でGoogle Sheetsに置き換えます) ---
if 'reports' not in st.session_state:
    # サンプルデータを入れておく
    st.session_state['reports'] = [
        {"Date": "2023-10-27", "User": "Taro", "Mood": "😁 快調", "Work": "開発:4h, MTG:2h", "Comment": "Streamlitの学習が進んだ。"},
        {"Date": "2023-10-26", "User": "Hanako", "Mood": "😅 普通", "Work": "設計:3h, 資料:3h", "Comment": "少し疲れ気味。早めに寝ます。"},
    ]

# --- ログイン状態の管理 ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'user_name' not in st.session_state:
    st.session_state['user_name'] = ""

# ==========================================
# 画面1: ログイン画面
# ==========================================
def login_page():
    st.markdown("## 🚶 Daily Walker")
    st.caption("チームのコンディションを可視化する")
    
    with st.container(border=True): # カードのような枠線
        email = st.text_input("Email", placeholder="user@example.com")
        password = st.text_input("Password", type="password")
        
        if st.button("サインイン", use_container_width=True, type="primary"):
            # 簡易的な認証チェック (本番はSheetsと照合)
            if email and password: 
                st.session_state['logged_in'] = True
                st.session_state['user_name'] = email.split('@')[0] # @より前を名前にする
                st.rerun() # 画面をリロードして切り替え
            else:
                st.error("入力してください")

# ==========================================
# 画面2: メインアプリ画面 (日報入力 & 一覧)
# ==========================================
def main_app():
    # サイドバー (ログアウトなど)
    with st.sidebar:
        st.write(f"ようこそ、**{st.session_state['user_name']}** さん")
        if st.button("ログアウト"):
            st.session_state['logged_in'] = False
            st.rerun()

    # タブで「書く」と「見る」を切り替え
    tab1, tab2 = st.tabs(["📝 日報を書く", "👀 みんなの日報"])

    # --- タブ1: 作成画面 ---
    with tab1:
        st.subheader("今日の振り返り")
        
        with st.form("daily_report_form"):
            # 日付とコンディションを横並びで
            col1, col2 = st.columns(2)
            with col1:
                report_date = st.date_input("日付", date.today())
            with col2:
                # コンディションを直感的に選択
                mood = st.selectbox("今日の調子は？", ["😁 快調", "🙂 普通", "😅 疲れ気味", "😵 SOS"])

            # 業務内訳 (スライダーで調整)
            st.markdown("**業務時間の内訳 (TaskWalker Style)**")
            dev_time = st.slider("💻 開発 / 実装", 0, 12, 4)
            mtg_time = st.slider("🗣 ミーティング", 0, 12, 2)
            doc_time = st.slider("📄 資料作成 / その他", 0, 12, 1)

            # ひとこと
            comment = st.text_area("所感・明日の予定", height=100, placeholder="今日はここがうまくいった、明日はこれをする、など")

            # 送信ボタン
            submitted = st.form_submit_button("日報を提出する", use_container_width=True, type="primary")

            if submitted:
                # データを保存する処理
                new_report = {
                    "Date": report_date.strftime('%Y-%m-%d'),
                    "User": st.session_state['user_name'],
                    "Mood": mood,
                    "Work": f"開発:{dev_time}h, MTG:{mtg_time}h, その他:{doc_time}h",
                    "Comment": comment
                }
                st.session_state['reports'].insert(0, new_report) # 先頭に追加
                st.success("お疲れ様でした！提出しました。")

    # --- タブ2: 一覧画面 (ダッシュボード) ---
    with tab2:
        st.subheader("チームのタイムライン")
        
        # データをDataFrameに変換して表示
        df = pd.DataFrame(st.session_state['reports'])
        
        # Streamlit標準のデータフレーム表示より、カード風に見せる
        for index, row in df.iterrows():
            with st.container(border=True):
                # ヘッダー行: 名前とコンディション
                c1, c2 = st.columns([3, 1])
                with c1:
                    st.markdown(f"**{row['User']}** <span style='color:gray; font-size:0.8em'>{row['Date']}</span>", unsafe_allow_html=True)
                with c2:
                    st.write(row['Mood'])
                
                # コンテンツ
                st.info(f"📊 {row['Work']}") # 青い帯で業務時間を表示
                st.write(row['Comment'])
                
                # リアクションボタン（見た目だけ）
                st.button("❤️ いいね", key=f"like_{index}", help="お疲れ様！")

# ==========================================
# アプリの起動制御
# ==========================================
if st.session_state['logged_in']:
    main_app()
else:
    login_page()
