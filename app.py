import streamlit as st
import pandas as pd
from datetime import datetime, date
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import uuid

# --- 設定 ---
SPREADSHEET_ID = '1mobXuRWq4fu1NZQsFm4Qw9-2uSVotttpefk9MWwOW54'
SHEET_NAME_REPORT = 'Reports'
SHEET_NAME_SETTINGS = 'Settings'
SHEET_NAME_PLANS = 'Plans'           # NEW
SHEET_NAME_PLAN_SETTINGS = 'PlanSettings' # NEW

st.set_page_config(page_title="作業日報システム", layout="wide")

# --- Google Sheets接続 ---
@st.cache_resource
def get_worksheet(sheet_name):
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds_dict = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        # シートがない場合は作成を試みる（エラー回避）
        try:
            ws = client.open_by_key(SPREADSHEET_ID).worksheet(sheet_name)
        except:
            # シートが存在しない場合、作成するロジックを入れると親切ですが、今回はエラー表示
            return None
        return ws
    except Exception as e:
        st.error(f"接続エラー ({sheet_name}): {e}")
        return None

# --- 共通関数: データ取得 ---
def get_data_as_df(sheet_name):
    sh = get_worksheet(sheet_name)
    if sh:
        data = sh.get_all_records()
        return pd.DataFrame(data)
    return pd.DataFrame()

# --- マスタデータ関連 ---
def get_options(category_name, factory_name=None):
    df = get_data_as_df(SHEET_NAME_SETTINGS)
    if not df.empty and 'category' in df.columns:
        df_cat = df[df['category'] == category_name]
        if factory_name and 'factory' in df.columns:
            df_cat = df_cat[df_cat['factory'] == factory_name]
        return df_cat['value'].tolist()
    return []

def add_option(factory, category, value):
    sh = get_worksheet(SHEET_NAME_SETTINGS)
    if sh:
        sh.append_row([factory, category, value])
        st.cache_data.clear()

# --- 日報保存 (ロット追加) ---
def save_report(data_dict):
    sh = get_worksheet(SHEET_NAME_REPORT)
    if sh:
        row = [
            datetime.now().strftime('%Y-%m-%d %H:%M'),
            data_dict['factory'],
            data_dict['worker'],
            data_dict['line'],
            data_dict['model'],
            data_dict['process_lot'], # NEW: 加工ロット
            data_dict['product'],
            data_dict['machine'],
            data_dict['k_ok'], data_dict['k_ng'],
            data_dict['r_ok'], data_dict['r_ng'],
            data_dict['note']
        ]
        sh.append_row(row)

# --- 計画関連 (NEW) ---
def save_plan(name, qty, due_date):
    sh = get_worksheet(SHEET_NAME_PLANS)
    if sh:
        plan_id = str(uuid.uuid4())[:8] # 短いIDを生成
        sh.append_row([plan_id, name, qty, str(due_date)])
        st.cache_data.clear()

def save_plan_mapping(plan_id, factory, line, machine, product, model, count_col):
    sh = get_worksheet(SHEET_NAME_PLAN_SETTINGS)
    if sh:
        sh.append_row([plan_id, factory, line, machine, product, model, count_col])
        st.cache_data.clear()

# --- セッション初期化 ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'role' not in st.session_state:
    st.session_state['role'] = "user"

# ==========================================
# 画面1: ログイン
# ==========================================
def login_page():
    st.markdown("## 🏭 作業日報システム")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.container(border=True):
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
            else:
                admin_pass = st.text_input("管理者パスワード", type="password")
                if st.button("管理者ログイン", type="primary", use_container_width=True):
                    if admin_pass == "admin123":
                        st.session_state['logged_in'] = True
                        st.session_state['role'] = "admin"
                        st.session_state['factory'] = "全社管理"
                        st.rerun()
                    else:
                        st.error("パスワードが違います")

# ==========================================
# 画面2: 管理者設定画面 (機能強化)
# ==========================================
def admin_page():
    st.title("🛠 管理者ダッシュボード")
    with st.sidebar:
        st.write("権限: 管理者")
        if st.button("ログアウト"):
            st.session_state['logged_in'] = False
            st.rerun()

    tab_progress, tab_plans, tab_master = st.tabs(["📈 進捗状況", "📅 計画登録・設定", "⚙️ マスタ管理"])

    # --- タブ1: 進捗状況 (予実管理) ---
    with tab_progress:
        st.subheader("生産計画 vs 実績")
        
        if st.button("データを更新", key="refresh_prog"):
            st.cache_data.clear()
            st.rerun()

        # データの準備
        df_plans = get_data_as_df(SHEET_NAME_PLANS)
        df_maps = get_data_as_df(SHEET_NAME_PLAN_SETTINGS)
        df_reports = get_data_as_df(SHEET_NAME_REPORT)

        if not df_plans.empty and not df_maps.empty and not df_reports.empty:
            for i, plan in df_plans.iterrows():
                plan_id = plan['plan_id']
                target_qty = int(plan['target_qty'])
                plan_name = plan['plan_name']
                
                # この計画に紐づく設定を取得
                my_maps = df_maps[df_maps['plan_id'] == plan_id]
                
                current_total = 0
                
                # 設定に基づいて日報を集計
                for j, mapping in my_maps.iterrows():
                    # フィルタリング
                    temp_df = df_reports.copy()
                    
                    if mapping['factory'] and mapping['factory'] != "指定なし":
                        temp_df = temp_df[temp_df['工場'] == mapping['factory']]
                    if mapping['machine'] and mapping['machine'] != "指定なし":
                        # カラム名が「機械」であることを想定
                        temp_df = temp_df[temp_df['機械'] == mapping['machine']]
                    if mapping['product'] and mapping['product'] != "指定なし":
                         temp_df = temp_df[temp_df['製品'] == mapping['product']]
                    
                    # カラム指定で集計 (k_ok:研削数, r_ok:ラバ数 と想定して変換)
                    # スプレッドシートのヘッダー名と合わせる必要があります
                    col_map = {"研削数": "研削数", "ラバ数": "ラバ数"} # 表示名:カラム名
                    target_col = mapping['count_column'] # 研削数 or ラバ数
                    
                    if target_col in temp_df.columns:
                         current_total += temp_df[target_col].sum()
                
                # 進捗率
                progress = min(current_total / target_qty, 1.0)
                diff = target_qty - current_total
                
                with st.container(border=True):
                    c1, c2 = st.columns([3, 1])
                    c1.markdown(f"**{plan_name}** (期限: {plan['due_date']})")
                    if diff > 0:
                        c2.error(f"残り {diff:,} 個")
                    else:
                        c2.success("達成完了！")
                    
                    st.progress(progress)
                    st.caption(f"実績: {current_total:,} / 計画: {target_qty:,} ({int(progress*100)}%)")
        else:
            st.info("計画または日報データがまだありません。")

    # --- タブ2: 計画登録・設定 ---
    with tab_plans:
        st.subheader("1. 新しい生産計画を作成")
        with st.form("new_plan"):
            p_name = st.text_input("計画名 (例: 7月度 UA25増産)")
            p_qty = st.number_input("目標数量", min_value=1, value=1000)
            p_date = st.date_input("期限")
            if st.form_submit_button("計画を作成"):
                save_plan(p_name, p_qty, p_date)
                st.success("計画を作成しました！次は下で紐付けを行ってください。")
        
        st.markdown("---")
        st.subheader("2. 計画と機械の紐付け")
        st.caption("どの計画が、どの機械の生産数でカウントされるかを設定します。")
        
        df_plans_curr = get_data_as_df(SHEET_NAME_PLANS)
        if not df_plans_curr.empty:
            plan_opts = df_plans_curr['plan_name'].tolist()
            plan_ids = df_plans_curr['plan_id'].tolist()
            
            selected_plan_name = st.selectbox("対象の計画を選択", plan_opts)
            selected_plan_id = plan_ids[plan_opts.index(selected_plan_name)]
            
            # フィルタ条件入力
            c1, c2, c3 = st.columns(3)
            # 既存のマスタから選択肢を取得
            f_opts = ["指定なし", "本社工場", "八尾工場"]
            m_opts = ["指定なし"] + get_options("machine")
            p_opts = ["指定なし"] + get_options("product")
            
            target_factory = c1.selectbox("工場 (フィルタ)", f_opts)
            target_machine = c2.selectbox("機械 (フィルタ)", m_opts)
            target_product = c3.selectbox("製品 (フィルタ)", p_opts)
            
            # どの数値をカウントするか
            count_target = st.radio("進捗判定に使う数値", ["研削数", "ラバ数"], horizontal=True)
            
            if st.button("紐付けを保存"):
                save_plan_mapping(selected_plan_id, target_factory, "指定なし", target_machine, target_product, "指定なし", count_target)
                st.success("設定を保存しました！")

    # --- タブ3: マスタ管理 (既存機能) ---
    with tab_master:
        st.info("項目追加")
        tf = st.selectbox("工場", ["本社工場", "八尾工場"])
        tc = st.selectbox("項目", ["line", "worker", "model", "product", "machine"])
        val = st.text_input("名称")
        if st.button("追加"):
            if val: add_option(tf, tc, val)

# ==========================================
# 画面3: 作業者ページ (ロット追加)
# ==========================================
def user_page():
    current_factory = st.session_state['factory']
    with st.sidebar:
        st.write(f"所属: **{current_factory}**")
        if st.button("ログアウト"):
            st.session_state['logged_in'] = False
            st.rerun()

    tab_input, tab_list = st.tabs(["📝 日報入力", "📊 履歴一覧"])

    with tab_input:
        st.subheader(f"作業日報 ({current_factory})")
        with st.form("work_report_form"):
            opt_lines = get_options("line", current_factory) or ["未登録"]
            opt_workers = get_options("worker", current_factory) or ["未登録"]
            opt_models = get_options("model", current_factory) or ["その他"]
            opt_products = get_options("product", current_factory) or ["その他"]
            opt_machines = get_options("machine", current_factory) or ["その他"]

            c1, c2 = st.columns(2)
            line = c1.selectbox("▎ライン種別", opt_lines)
            worker = c2.selectbox("▎作業者", opt_workers)

            c3, c4 = st.columns(2)
            model = c3.selectbox("▎型番", opt_models)
            # NEW: 加工ロット入力
            process_lot = c4.text_input("▎加工ロット (追加項目)")

            c5, c6 = st.columns(2)
            product = c5.selectbox("▎製品種別", opt_products)
            machine = c6.selectbox("▎機械種別", opt_machines)

            st.markdown("---")
            c_k1, c_k2 = st.columns(2)
            k_ok = c_k1.number_input("▎研削 研磨数", min_value=0)
            k_ng = c_k2.number_input("▎研削 不良数", min_value=0)
            
            c_r1, c_r2 = st.columns(2)
            r_ok = c_r1.number_input("▎ラバ研 研磨数", min_value=0)
            r_ng = c_r2.number_input("▎ラバ研 不良数", min_value=0)

            note = st.text_area("▎備考")

            if st.form_submit_button("提出", type="primary", use_container_width=True):
                report_data = {
                    "factory": current_factory,
                    "worker": worker, "line": line, "model": model,
                    "product": product, "machine": machine,
                    "process_lot": process_lot, # 保存データに追加
                    "k_ok": k_ok, "k_ng": k_ng, "r_ok": r_ok, "r_ng": r_ng,
                    "note": note
                }
                save_report(report_data)
                st.success("保存しました！")

    with tab_list:
        if st.button("更新"): st.rerun()
        df = load_reports()
        if not df.empty:
            df_filtered = df[df['工場'] == current_factory]
            st.dataframe(df_filtered, use_container_width=True, hide_index=True)

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
