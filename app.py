import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- 設定 ---
SPREADSHEET_ID = '1mobXuRWq4fu1NZQsFm4Qw9-2uSVotttpefk9MWwOW54' # あなたのIDのまま
SHEET_NAME_REPORT = 'Reports'
SHEET_NAME_SETTINGS = 'Settings' # 新しく作ったシート

st.set_page_config(page_title="作業日報システム", layout="wide")

# --- Google Sheets接続 ---
@st.cache_resource
def get_worksheet(sheet_name):
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds_dict = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client.open_by_key(SPREADSHEET_ID).worksheet(sheet_name)
    except Exception as e:
        st.error(f"接続エラー ({sheet_name}): {e}")
        return None

# --- マスタデータ（選択肢）の読み込み ---
def get_options(category_name):
    sh = get_worksheet(SHEET_NAME_SETTINGS)
    if sh:
        data = sh.get_all_records()
        df = pd.DataFrame(data)
        # category列が一致するものだけを抽出してリスト化
        if not df.empty and 'category' in df.columns:
            return df[df['category'] == category_name]['value'].tolist()
    return [] # データがない場合は空リスト

# --- マスタデータ（選択肢）の追加 ---
def add_option(category, value):
    sh = get_worksheet(SHEET_NAME_SETTINGS)
    if sh:
        sh.append_row([category, value])
        st.cache_data.clear() # キャッシュを消して即座に反映

# --- 日報保存 ---
def save_report(data_dict):
    sh = get_worksheet(SHEET_NAME_REPORT)
    if sh:
        row = [
            datetime.now().strftime('%Y-%m-%d %H:%M'),
            data_dict['factory'],
            data_dict['worker'],
            data_dict['line'],
            data_dict['model'],
            data_dict['product'],
            data_dict['machine'],
            data_dict['k_ok'], data_dict['k_ng'],
            data_dict['r_ok'], data_dict['r_ng'],
            data_dict['note']
        ]
        sh.append_row(row)

# --- 履歴読み込み ---
def load_reports():
    sh = get_worksheet(SHEET_NAME_REPORT)
    if sh:
        data = sh.get_all_records()
        return pd.DataFrame(data)
    return pd.DataFrame()

# --- セッション初期化 ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'role' not in st.session_state:
    st.session_state['role'] = "user" # user か admin

# ==========================================
# 画面1: ログイン (管理者を追加)
# ==========================================
def login_page():
    st.markdown("## 🏭 作業日報システム")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.container(border=True):
            # ログインタイプ選択
            login_type = st.radio("ログイン種別", ["作業者", "管理者"], horizontal=True)
            
            if login_type == "作業者":
                factory = st.selectbox("工場", ["本社工場", "八尾工場"])
                password = st.text_input("パスワード", type="password")
                if st.button("ログイン", type="primary", use_container_width=True):
                    if (factory == "本社工場" and password == "honsha") or \
                       (factory == "八尾工場" and password == "yao"):
                        st.session_state['logged_in'] = True
                        st.session_state['role'] = "user"
                        st.session_state['factory'] = factory
                        st.rerun()
                    else:
                        st.error("パスワードが違います")
            
            else: # 管理者ログイン
                admin_pass = st.text_input("管理者パスワード", type="password")
                if st.button("管理者ログイン", type="primary", use_container_width=True):
                    if admin_pass == "admin123": # 仮の管理者パスワード
                        st.session_state['logged_in'] = True
                        st.session_state['role'] = "admin"
                        st.session_state['factory'] = "全社管理"
                        st.rerun()
                    else:
                        st.error("パスワードが違います")

# ==========================================
# 画面2: 管理者設定画面 (NEW!)
# ==========================================
def admin_page():
    st.title("🛠 管理者設定画面")
    
    with st.sidebar:
        st.write("ログイン中: 管理者")
        if st.button("ログアウト"):
            st.session_state['logged_in'] = False
            st.rerun()

    st.info("ここでドロップダウンの選択肢を追加できます。")

    # 追加したいカテゴリを選択
    target_cat = st.selectbox("編集する項目を選択", [
        "line", "worker", "model", "product", "machine"
    ], format_func=lambda x: {
        "line": "ライン種別", "worker": "作業者", "model": "型番", 
        "product": "製品種別", "machine": "機械種別"
    }[x])

    # 現在のリストを表示
    current_list = get_options(target_cat)
    st.write(f"▼ 現在の登録済みリスト ({len(current_list)}件)")
    st.code(", ".join(current_list) if current_list else "(登録なし)")

    # 新規追加フォーム
    with st.form("add_master_form"):
        new_value = st.text_input("追加する名称を入力")
        if st.form_submit_button("追加する", type="primary"):
            if new_value and new_value not in current_list:
                add_option(target_cat, new_value)
                st.success(f"「{new_value}」を追加しました！")
                st.rerun()
            elif new_value in current_list:
                st.warning("その名称は既に登録されています。")
            else:
                st.warning("名称を入力してください。")

    st.markdown("---")
    st.subheader("📊 全データ確認")
    if st.button("日報データを読み込む"):
        df = load_reports()
        st.dataframe(df)

# ==========================================
# 画面3: 作業者ページ (選択肢を動的に変更)
# ==========================================
def user_page():
    with st.sidebar:
        st.write(f"所属: **{st.session_state['factory']}**")
        if st.button("ログアウト"):
            st.session_state['logged_in'] = False
            st.rerun()

    tab_input, tab_list = st.tabs(["📝 日報入力", "📊 履歴一覧"])

    with tab_input:
        st.subheader("作業日報入力")
        with st.form("work_report_form"):
            # スプレッドシートから選択肢を取得
            # データがない場合のデフォルト値も設定
            opt_lines = get_options("line") or ["(管理者が未登録)"]
            opt_workers = get_options("worker") or ["(管理者が未登録)"]
            opt_models = get_options("model") or ["その他"]
            opt_products = get_options("product") or ["その他"]
            opt_machines = get_options("machine") or ["その他"]

            c1, c2 = st.columns(2)
            line = c1.selectbox("▎ライン種別", opt_lines)
            worker = c2.selectbox("▎作業者", opt_workers)

            model = st.selectbox("▎型番", ["検索..."] + opt_models)

            c3, c4 = st.columns(2)
            product = c3.selectbox("▎製品種別", opt_products)
            machine = c4.selectbox("▎機械種別", opt_machines)

            st.markdown("---")
            # 数値入力など（変更なし）
            c_k1, c_k2 = st.columns(2)
            k_ok = c_k1.number_input("▎研削 研磨数", min_value=0)
            k_ng = c_k2.number_input("▎研削 不良数", min_value=0)
            
            c_r1, c_r2 = st.columns(2)
            r_ok = c_r1.number_input("▎ラバ研 研磨数", min_value=0)
            r_ng = c_r2.number_input("▎ラバ研 不良数", min_value=0)

            note = st.text_area("▎備考")

            if st.form_submit_button("日報を提出", type="primary", use_container_width=True):
                report_data = {
                    "factory": st.session_state['factory'],
                    "worker": worker, "line": line, "model": model,
                    "product": product, "machine": machine,
                    "k_ok": k_ok, "k_ng": k_ng, "r_ok": r_ok, "r_ng": r_ng,
                    "note": note
                }
                save_report(report_data)
                st.success("保存しました！")

    with tab_list:
        if st.button("最新データ取得"):
            st.cache_data.clear()
            st.rerun()
        df = load_reports()
        if not df.empty:
            st.dataframe(df, use_container_width=True, hide_index=True)

# ==========================================
# メイン処理
# ==========================================
if st.session_state['logged_in']:
    if st.session_state['role'] == "admin":
        admin_page()
    else:
        user_page()
else:
    login_page()
