import streamlit as st
import pandas as pd
from datetime import datetime, date
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- 設定 ---
SPREADSHEET_ID = '1mobXuRWq4fu1NZQsFm4Qw9-2uSVotttpefk9MWwOW54'
SHEET_NAME_REPORT = 'Reports'
SHEET_NAME_SETTINGS = 'Settings'
SHEET_NAME_SCHEDULE = 'Schedule'
SHEET_NAME_RULES = 'CountingRules'

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
        return None

# --- データ取得・保存 ---
def get_data_as_df(sheet_name):
    sh = get_worksheet(sheet_name)
    if sh:
        data = sh.get_all_records()
        return pd.DataFrame(data).astype(str)
    return pd.DataFrame()

def save_report(data_dict):
    sh = get_worksheet(SHEET_NAME_REPORT)
    if sh:
        row = [
            datetime.now().strftime('%Y-%m-%d %H:%M'),
            data_dict['factory'],
            data_dict['worker'],
            data_dict['line'],
            data_dict['model'],
            data_dict['process_lot'],
            data_dict['product'],
            data_dict['machine'],
            data_dict['k_ok'], data_dict['k_ng'],
            data_dict['r_ok'], data_dict['r_ng'],
            data_dict['note']
        ]
        sh.append_row(row)
        st.cache_data.clear()

# --- マスタ管理 ---
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

# --- 計画・ルール保存 ---
def save_counting_rule(factory, line, model, machine, column):
    sh = get_worksheet(SHEET_NAME_RULES)
    if sh:
        sh.append_row([factory, line, model, machine, column])
        st.cache_data.clear()

def append_schedule_data(factory_name, df_input):
    sh = get_worksheet(SHEET_NAME_SCHEDULE)
    if sh:
        rows_to_save = []
        for index, row in df_input.iterrows():
            qty_str = str(row.get('数量', '0')).replace(',', '')
            new_row = [
                str(row.get('日付', '')),
                factory_name,
                str(row.get('ライン', '')),
                str(row.get('型番', '')),
                str(row.get('ロット', '')),
                qty_str
            ]
            rows_to_save.append(new_row)
        for r in rows_to_save:
            sh.append_row(r)
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
                    if (factory == "本社工場" and password == "3457") or \
                       (factory == "八尾工場" and password == "3457"):
                        st.session_state['logged_in'] = True
                        st.session_state['role'] = "user"
                        st.session_state['factory'] = factory
                        st.rerun()
                    else:
                        st.error("パスワードが違います")
            else:
                admin_pass = st.text_input("管理者パスワード", type="password")
                if st.button("管理者ログイン", type="primary", use_container_width=True):
                    if admin_pass == "mbss3457":
                        st.session_state['logged_in'] = True
                        st.session_state['role'] = "admin"
                        st.session_state['factory'] = "全社管理"
                        st.rerun()
                    else:
                        st.error("パスワードが違います")

# ==========================================
# 画面2: 管理者ダッシュボード
# ==========================================
def admin_page():
    st.title("🛠 管理者ダッシュボード")
    with st.sidebar:
        st.write("権限: 管理者")
        if st.button("ログアウト"):
            st.session_state['logged_in'] = False
            st.rerun()

    tab_progress, tab_plan_upload, tab_rules, tab_master = st.tabs([
        "📈 進捗管理", "📥 計画アップロード", "⚙️ 判定ルール", "📝 項目マスタ"
    ])

    # --- タブ1: 進捗管理 ---
    with tab_progress:
        st.subheader("生産進捗モニタリング (ロット別)")
        if st.button("最新データ更新"):
            st.cache_data.clear()
            st.rerun()

        df_schedule = get_data_as_df(SHEET_NAME_SCHEDULE)
        df_reports = get_data_as_df(SHEET_NAME_REPORT)
        df_rules = get_data_as_df(SHEET_NAME_RULES)

        if df_schedule.empty:
            st.info("計画データがありません。「計画アップロード」から登録してください。")
        else:
            today_str = date.today().strftime('%Y-%m-%d')
            progress_data = []

            for i, plan in df_schedule.iterrows():
                p_date = plan['date']
                p_factory = plan['factory']
                p_line = plan['line']
                p_model = plan['model']
                p_lot = str(plan['lot'])
                try:
                    p_qty = int(str(plan['plan_qty']).replace(',', ''))
                except:
                    p_qty = 0

                # ルール検索
                target_machine = None
                target_col = "研削数"
                if not df_rules.empty:
                    rules = df_rules[
                        (df_rules['factory'] == p_factory) & 
                        (df_rules['line'] == p_line) & 
                        (df_rules['model'] == p_model)
                    ]
                    if not rules.empty:
                        target_machine = rules.iloc[0]['target_machine']
                        target_col = rules.iloc[0]['target_column']

                # 実績集計
                actual_qty = 0
                if not df_reports.empty:
                    mask = (
                        (df_reports['工場'] == p_factory) &
                        (df_reports['ライン'] == p_line) &
                        (df_reports['型番'] == p_model) &
                        (df_reports['ロット'].astype(str) == p_lot)
                    )
                    if target_machine and target_machine != "指定なし":
                        mask = mask & (df_reports['機械'] == target_machine)
                    filtered = df_reports[mask]
                    col_name = "研削数" 
                    if target_col == "ラバ数": col_name = "ラバ数"
                    if col_name in filtered.columns:
                        actual_qty = pd.to_numeric(filtered[col_name], errors='coerce').fillna(0).sum()

                # ステータス
                diff = actual_qty - p_qty
                status = "進行中"
                if diff >= 0:
                    status = "完了"
                elif p_date < today_str:
                    status = "遅延"

                progress_data.append({
                    "日付": p_date,
                    "工場": p_factory,
                    "ライン": p_line,
                    "型番": p_model,
                    "ロット": p_lot,
                    "計画数": p_qty,
                    "実績数": int(actual_qty),
                    "残数": int(p_qty - actual_qty) if diff < 0 else 0,
                    "状態": status,
                    "判定機械": target_machine or "(全機械)"
                })

            df_res = pd.DataFrame(progress_data)
            def highlight_status(val):
                color = ''
                if val == '遅延': color = 'background-color: #ffcccc'
                elif val == '完了': color = 'background-color: #ccffcc'
                return color

            st.dataframe(
                df_res.style.map(highlight_status, subset=['状態']),
                use_container_width=True,
                height=600
            )

    # --- タブ2: 計画アップロード ---
    with tab_plan_upload:
        st.subheader("生産計画データの登録")
        target_factory = st.selectbox("対象工場を選択してください", ["本社工場", "八尾工場"])
        st.markdown("---")
        st.info("Excelから以下の5列をコピーして貼り付けてください。")
        st.caption("並び順: **日付 | ライン | 型番 | ロット | 数量**")

        template_data = {
            "日付": ["2025-01-01"], 
            "ライン": ["ラインA"], 
            "型番": ["UA25"], 
            "ロット": ["12345"], 
            "数量": [1000]
        }
        df_template = pd.DataFrame(template_data)
        edited_df = st.data_editor(
            df_template,
            num_rows="dynamic",
            use_container_width=True,
            key="schedule_editor"
        )
        if st.button("計画を保存する", type="primary"):
            if not edited_df.empty:
                append_schedule_data(target_factory, edited_df)
                st.success("✅ スプレッドシートに登録しました！")
            else:
                st.warning("データがありません")

    # --- タブ3: 判定ルール設定 ---
    with tab_rules:
        st.subheader("進捗判定ルールの設定")
        f_list = ["本社工場", "八尾工場"]
        c1, c2 = st.columns(2)
        r_factory = c1.selectbox("工場", f_list)
        l_list = get_options("line", r_factory)
        m_list = get_options("model", r_factory)
        mac_list = get_options("machine", r_factory)

        r_line = c2.selectbox("ライン", l_list)
        r_model = c1.selectbox("型番 (Model)", ["(指定なし)"] + m_list)
        
        col_rule1, col_rule2 = st.columns(2)
        r_target_machine = col_rule1.selectbox("判定機械 (完了とする機械)", mac_list)
        r_target_col = col_rule2.radio("判定数値", ["研削数", "ラバ数"], horizontal=True)

        if st.button("ルールを保存"):
            save_counting_rule(r_factory, r_line, r_model, r_target_machine, r_target_col)
            st.success("保存しました")
        
        st.write("▼ 現在のルール一覧")
        df_rules_curr = get_data_as_df(SHEET_NAME_RULES)
        if not df_rules_curr.empty:
            st.dataframe(df_rules_curr)

    # --- タブ4: マスタ管理 (日本語化修正) ---
    with tab_master:
        st.subheader("項目マスタ管理")
        st.caption("新しいラインや製品名を追加します。")

        # 工場選択
        tf = st.selectbox("追加先工場", ["本社工場", "八尾工場"], key="mst_fac")

        # カテゴリの日本語マップ
        category_map = {
            "line": "ライン種別",
            "worker": "作業者",
            "model": "型番",
            "product": "製品種別",
            "machine": "機械種別"
        }

        # 辞書のキー(line等)を使いつつ、表示は値(ライン種別等)にする
        tc_key = st.selectbox(
            "追加する項目の種類", 
            options=list(category_map.keys()), 
            format_func=lambda x: category_map[x]
        )

        val = st.text_input("追加する名称 (例: ラインC, 新人A)")
        
        if st.button("追加実行", type="primary"):
            if val:
                add_option(tf, tc_key, val)
                st.success(f"「{tf}」の「{category_map[tc_key]}」に「{val}」を追加しました")
            else:
                st.warning("名称を入力してください")

# ==========================================
# 画面3: 作業者ページ
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
            process_lot = c4.text_input("▎加工ロット")

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
                    "process_lot": process_lot,
                    "k_ok": k_ok, "k_ng": k_ng, "r_ok": r_ok, "r_ng": r_ng,
                    "note": note
                }
                save_report(report_data)
                st.success("保存しました！")

    with tab_list:
        if st.button("更新"): st.rerun()
        df = get_data_as_df(SHEET_NAME_REPORT)
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
