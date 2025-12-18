import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- 設定 ---
# 以前教えていただいたスプレッドシートID
SPREADSHEET_ID = '1mobXuRWq4fu1NZQsFm4Qw9-2uSVotttpefk9MWwOW54/edit?gid=0#gid=0'
SHEET_NAME = 'Reports' # シート名を「Reports」に変更するか、ここを実際のシート名に合わせてください

st.set_page_config(page_title="作業日報システム", layout="wide") # 一覧が見やすいようにwideモードに変更

# --- Google Sheets接続設定 ---
@st.cache_resource
def get_worksheet():
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        # Streamlit CloudのSecretsから認証情報を取得
        creds_dict = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)
    except Exception as e:
        st.error(f"スプレッドシート接続エラー: {e}")
        return None

# --- データ保存関数 ---
def save_report(data_dict):
    sh = get_worksheet()
    if sh:
        # 辞書の値（入力データ）をリストにして追加
        # 保存する順番: 日付, 工場, 作業者, ライン, 型番, 製品, 機械, 研削数, 不良数...
        row = [
            datetime.now().strftime('%Y-%m-%d %H:%M'),
            data_dict['factory'],
            data_dict['worker'],
            data_dict['line'],
            data_dict['model'],
            data_dict['product'],
            data_dict['machine'],
            data_dict['k_ok'], # 研削 良品
            data_dict['k_ng'], # 研削 不良
            data_dict['r_ok'], # ラバ研 良品
            data_dict['r_ng'], # ラバ研 不良
            data_dict['note']
        ]
        sh.append_row(row)

# --- データ読み込み関数 ---
def load_data():
    sh = get_worksheet()
    if sh:
        data = sh.get_all_records()
        return pd.DataFrame(data)
    return pd.DataFrame()

# --- セッション初期化 ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'factory' not in st.session_state:
    st.session_state['factory'] = ""

# ==========================================
# 画面1: ログイン
# ==========================================
def login_page():
    st.markdown("## 🏭 作業日報システム")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.container(border=True):
            factory = st.selectbox("工場", ["本社工場", "八尾工場"])
            password = st.text_input("パスワード", type="password")
            if st.button("ログイン", type="primary", use_container_width=True):
                if (factory == "本社工場" and password == "honsha") or \
                   (factory == "八尾工場" and password == "yao"):
                    st.session_state['logged_in'] = True
                    st.session_state['factory'] = factory
                    st.rerun()
                else:
                    st.error("パスワードが違います")

# ==========================================
# 画面2: メイン（入力 ＆ 一覧）
# ==========================================
def main_page():
    # サイドバー
    with st.sidebar:
        st.write(f"所属: **{st.session_state['factory']}**")
        if st.button("ログアウト"):
            st.session_state['logged_in'] = False
            st.rerun()

    # タブで画面切り替え
    tab_input, tab_list = st.tabs(["📝 日報入力", "📊 履歴一覧"])

    # --- タブ1: 入力画面 ---
    with tab_input:
        st.subheader("作業日報入力")
        
        # フォームとしてまとめることで、途中でリロードされるのを防ぎます
        with st.form("work_report_form"):
            c1, c2 = st.columns(2)
            line = c1.selectbox("▎ライン種別", ["外径ライン", "組み立てライン", "3号ライン"])
            worker = c2.selectbox("▎作業者", ["廣瀬", "青井", "門", "坂本"])

            model = st.selectbox("▎型番", ["UA25", "SN6311T071", "RNU205ETW2", "その他"])

            c3, c4 = st.columns(2)
            product = c3.selectbox("▎製品種別", ["SHI", "韓国", "シリンドリカル"])
            machine = c4.selectbox("▎機械種別", ["センターレス1号機", "T11J", "組立機1号機"])

            st.markdown("---")
            # 数値入力エリア
            c_k1, c_k2 = st.columns(2)
            k_ok = c_k1.number_input("▎研削 研磨数", min_value=0, step=1)
            k_ng = c_k2.number_input("▎研削 不良数", min_value=0, step=1)
            
            c_r1, c_r2 = st.columns(2)
            r_ok = c_r1.number_input("▎ラバ研 研磨数", min_value=0, step=1)
            r_ng = c_r2.number_input("▎ラバ研 不良数", min_value=0, step=1)

            note = st.text_area("▎備考")

            # 送信ボタン
            submitted = st.form_submit_button("日報を提出（保存）", type="primary", use_container_width=True)

            if submitted:
                # データをまとめる
                report_data = {
                    "factory": st.session_state['factory'],
                    "worker": worker,
                    "line": line,
                    "model": model,
                    "product": product,
                    "machine": machine,
                    "k_ok": k_ok, "k_ng": k_ng,
                    "r_ok": r_ok, "r_ng": r_ng,
                    "note": note
                }
                
                # 保存処理実行
                with st.spinner("保存中..."):
                    save_report(report_data)
                
                st.success("✅ スプレッドシートに保存しました！")
                st.cache_data.clear() # キャッシュをクリアして一覧を最新にする

    # --- タブ2: 一覧画面 ---
    with tab_list:
        st.subheader("作業履歴一覧")
        
        # データの読み込み
        if st.button("🔄 最新データを取得"):
            st.cache_data.clear()
        
        df = load_data()
        
        if not df.empty:
            # 工場でフィルタリング（自分の工場のデータだけ見る場合）
            # df = df[df['工場'] == st.session_state['factory']] 
            
            # 見やすいようにテーブル表示
            st.dataframe(
                df, 
                use_container_width=True,
                height=500,
                hide_index=True
            )
        else:
            st.info("データがまだありません。日報を入力してください。")

# ==========================================
# 起動制御
# ==========================================
if st.session_state['logged_in']:
    main_page()
else:
    login_page()
