"""Textos de la interfaz en inglés y japonés.

Para agregar o corregir un texto basta con editar este diccionario:
clave → (inglés, japonés). Los valores entre llaves {así} se reemplazan.
"""

from __future__ import annotations

from collections.abc import Callable

TEXTS: dict[str, tuple[str, str]] = {
    # ── General ──
    "loading": ("Loading data…", "データを読み込み中…"),
    "saving": ("Saving…", "保存中…"),
    "save": ("Save", "保存"),
    "saved": ("Saved.", "保存しました。"),
    "save_failed": ("Could not save.", "保存できませんでした。"),
    "load_failed": ("Could not load the data.", "データを読み込めませんでした。"),
    "retry": ("Retry", "再試行"),
    "refresh": ("Refresh data", "データを更新"),
    "refresh_help": ("Reload the latest data saved by all users.", "全ユーザーが保存した最新データを再読み込みします。"),
    "language": ("Language", "言語"),
    "view": ("View", "表示"),
    "view_admin": ("Admin", "管理者"),
    "view_supervisor": ("Supervisor", "監督者"),
    "role_admin": ("Admin", "管理者"),
    "role_supervisor": ("Supervisor", "監督者"),
    "role_master": ("Master", "マスター"),
    "all": ("All", "すべて"),
    "today": ("Today", "本日"),
    "when": ("When", "日時"),
    "who": ("Who", "担当者"),
    "kind": ("Type", "種類"),
    "change": ("Change", "変更内容"),
    "data_source": ("Data", "データ"),
    "subtitle_admin": ("Project control", "プロジェクト管理"),
    "subtitle_supervisor": ("Field progress", "現場進捗入力"),
    "no_data": ("No data yet.", "データがありません。"),
    "no_changes": ("Nothing changed.", "変更はありません。"),

    # ── Inicio de sesión y contraseña ──
    "login": ("Sign in", "ログイン"),
    "logout": ("Sign out", "ログアウト"),
    "public_subtitle": ("View · countermeasure status (read only)", "閲覧 · 対策の進捗（閲覧のみ）"),
    "public_help": ("Read-only view of the countermeasure roll-out. Sign in on the right to record progress or manage the plan.",
                    "対策展開状況の閲覧専用ページです。進捗の入力や計画の管理は、右側からログインしてください。"),
    "public_footer": ("Read-only view", "閲覧専用"),
    "login_failed": ("Incorrect username or password.", "ユーザー名またはパスワードが正しくありません。"),
    "login_help": ("Forgot your password? Ask the app owner to reset it.",
                   "パスワードを忘れた場合は、アプリのオーナーにリセットを依頼してください。"),
    "username": ("Username", "ユーザー名"),
    "password": ("Password", "パスワード"),
    "confirm_password": ("Confirm password", "パスワード（確認）"),
    "password_help": ("At least 8 characters.", "8文字以上。"),
    "change_password": ("Change my password", "パスワード変更"),
    "current_password": ("Current password", "現在のパスワード"),
    "new_password": ("New password", "新しいパスワード"),
    "password_changed": ("Password changed.", "パスワードを変更しました。"),
    "err_password_short": ("The password must have at least 8 characters.", "パスワードは8文字以上にしてください。"),
    "err_password_match": ("The passwords do not match.", "パスワードが一致しません。"),
    "err_current_password": ("The current password is incorrect.", "現在のパスワードが正しくありません。"),

    # ── Inicialización ──
    "not_initialized": ("The project has not been loaded yet. An admin must load it first.",
                        "プロジェクトはまだ読み込まれていません。管理者が最初に読み込む必要があります。"),
    "init_help": ("First use: load the 20 countermeasures and the truck status from the progress tracker (Excel, 19-Oct-26) "
                  "and the action plan.", "初回利用：進捗トラッカー（Excel、2026年10月19日版）と実行計画から20件の対策と車両の状況を読み込みます。"),
    "init_button": ("Load the plan from the tracker", "トラッカーから計画を読み込む"),

    # ── Estados ──
    "st_closed": ("Closed out", "完了（書類済）"),
    "st_executed": ("Executed · docs open", "実施済・書類未了"),
    "st_in_progress": ("In progress", "進行中"),
    "st_not_started": ("Not started", "未着手"),
    "st_na": ("N/A", "対象外"),
    "cst_done": ("Done", "完了"),
    "cst_overdue": ("Overdue", "期限超過"),
    "cst_due_soon": ("Due soon", "期限間近"),
    "cst_on_track": ("On track", "予定どおり"),
    "cst_no_target": ("No target", "目標日なし"),

    # ── KPI ──
    "kpi_executed": ("Fleet executed", "フリート実施率"),
    "kpi_executed_sub": ("{e} of {n} truck-jobs", "{n}件中 {e}件"),
    "kpi_closed": ("Fully closed out", "書類まで完了"),
    "kpi_closed_sub": ("FIR uploaded and report filed", "FIR登録・報告書提出済み"),
    "kpi_cms_done": ("Countermeasures done", "完了した対策"),
    "kpi_cms_done_sub": ("Every applicable truck executed", "対象車両すべて実施済み"),
    "kpi_overdue": ("Past target date", "目標日超過"),
    "kpi_overdue_sub": ("Target passed, fleet not finished", "目標日を過ぎて未完了"),

    # ── Campos ──
    "countermeasure": ("Countermeasure", "対策"),
    "truck": ("Truck", "車両"),
    "model": ("Model", "機種"),
    "serial": ("Serial", "シリアル"),
    "name": ("Name", "名称"),
    "responsible": ("Responsible", "担当者"),
    "target": ("Fleet target", "フリート目標日"),
    "duration": ("Duration per machine", "1台あたり所要時間"),
    "duration_help": ("Example: 12 h", "例：12 h"),
    "action_required": ("Action required", "必要な対応"),
    "status": ("Status", "状況"),
    "executed": ("Executed", "実施済"),
    "closed_out": ("Closed out", "書類完了"),
    "applicable": ("Applicable", "対象"),
    "fleet_pct": ("Fleet % executed", "フリート実施率"),
    "closed_pct": ("% closed out", "書類完了率"),
    "col_no": ("No.", "No."),
    "planned": ("Planned", "計画済"),
    "fir": ("FIR uploaded", "FIR登録"),
    "report": ("Report / timesheets", "報告書・作業時間"),
    "planned_date": ("Planned date", "計画日"),
    "work_order": ("Work order", "作業指示番号"),
    "exec_date": ("Execution date", "実施日"),
    "note": ("Note", "メモ"),
    "na": ("N/A", "対象外"),
    "na_help": ("The countermeasure does not apply to this truck. Only admins can change it.",
                "この車両には対策が適用されません。管理者のみ変更できます。"),
    "progress": ("Progress", "進捗"),
    "last_update": ("Last update", "最終更新"),
    "steps": ("Execution steps", "実施項目"),
    "step_help": ("Tick when this part of the work is executed.", "この作業を実施したらチェックします。"),
    "days_left": ("{d} days left", "残り{d}日"),
    "days_late": ("{d} days late", "{d}日超過"),

    # ── Supervisor ──
    "work_by": ("Work by", "入力方法"),
    "work_by_cm": ("Countermeasure", "対策ごと"),
    "work_by_truck": ("Truck", "車両ごと"),
    "filter_status": ("Show", "表示"),
    "search_fleet": ("Find fleet # or WO", "車両番号・作業指示で検索"),
    "truck_mode_help": ("“Executed” ticks every execution step of that countermeasure (e.g. RHS and LHS). "
                        "To tick sides separately, work by countermeasure.",
                        "「実施済」はその対策のすべての実施項目（例：右・左）をチェックします。左右を別々に入力する場合は「対策ごと」で入力してください。"),
    "no_rows": ("No trucks match this filter.", "条件に合う車両はありません。"),
    "save_changes": ("Save changes", "変更を保存"),
    "pending_changes": ("{n} rows changed — not saved yet.", "{n}行が変更されています（未保存）。"),
    "autofill_help": ("Ticking every execution step fills today's date as execution date if it is empty.",
                      "すべての実施項目をチェックすると、実施日が空欄の場合は本日の日付が入ります。"),
    "saved_rows": ("Saved {n} rows.", "{n}行を保存しました。"),
    "history_n": ("Change history ({n})", "変更履歴（{n}）"),
    "no_history": ("No changes recorded yet.", "変更履歴はまだありません。"),

    # ── Administrador ──
    "tab_summary": ("Summary", "概要"),
    "tab_matrix": ("Top page", "一覧表"),
    "tab_progress": ("Progress", "進捗入力"),
    "tab_cms": ("Countermeasures", "対策"),
    "tab_trucks": ("Trucks", "車両"),
    "tab_reports": ("Reports", "レポート"),
    "tab_settings": ("Settings", "設定"),
    "alerts_n": ("Alerts ({n})", "アラート（{n}）"),
    "no_alerts": ("No open alerts.", "未対応のアラートはありません。"),
    "alert_title_overdue": ("Past the fleet target", "フリート目標日超過"),
    "alert_title_due_soon": ("Fleet target approaching", "フリート目標日が近い"),
    "alert_title_planned_missed": ("Planned date passed, not executed", "計画日を過ぎて未実施"),
    "alert_title_docs_pending": ("Executed, documents missing", "実施済・書類未了"),
    "alert_overdue": ("Target passed {days} days ago; {left} trucks still to execute.",
                      "目標日を{days}日超過。残り{left}台が未実施です。"),
    "alert_due_soon": ("Target in {days} days; {left} trucks still to execute.", "目標日まで{days}日。残り{left}台が未実施です。"),
    "alert_planned_missed": ("{n} trucks: {fleets}", "{n}台：{fleets}"),
    "alert_docs_pending": ("{n} trucks need FIR or report: {fleets}", "{n}台でFIRまたは報告書が未提出：{fleets}"),
    "action_plan": ("Countermeasure task list — action plan", "対策タスクリスト — 実行計画"),
    "recent_changes": ("Recent changes", "最近の変更"),
    "edit_cm": ("Edit a countermeasure", "対策の編集"),
    "steps_fixed": ("Execution steps: {steps}. They are fixed once trucks have progress recorded.",
                    "実施項目：{steps}。進捗が登録された後は変更できません。"),
    "add_cm": ("Add countermeasure", "対策を追加"),
    "steps_help": ("Comma-separated, e.g. “RHS, LHS”. Leave “Executed” for a single step.",
                   "カンマ区切り（例：RHS, LHS）。1項目の場合は「Executed」のまま。"),
    "copy_trucks_from": ("Trucks it applies to (copy list from)", "対象車両（コピー元）"),
    "no_trucks": ("No trucks yet — add them in the Trucks tab", "車両なし（車両タブで追加）"),
    "err_name": ("Enter a name.", "名称を入力してください。"),
    "cm_added": ("Countermeasure “{name}” added.", "対策「{name}」を追加しました。"),
    "remove_cm": ("Remove countermeasure", "対策を削除"),
    "confirm_remove_cm": ("I understand this removes the countermeasure and its truck records from the tracker (history is kept).",
                          "対策と車両記録が一覧から削除されることを理解しました（履歴は残ります）。"),
    "cm_removed": ("Countermeasure removed.", "対策を削除しました。"),
    "err_confirm": ("Tick the confirmation box first.", "確認のチェックを入れてください。"),
    "fleet_summary": ("Fleet", "フリート"),
    "add_truck": ("Add truck", "車両を追加"),
    "applies_to": ("Countermeasures that apply", "適用する対策"),
    "err_fleet": ("Fleet number: 2–12 letters or digits, e.g. RD232.", "車両番号：英数字2〜12文字（例：RD232）。"),
    "err_pick_cm": ("Pick at least one countermeasure.", "対策を1つ以上選択してください。"),
    "truck_added": ("{fleet} added.", "{fleet}を追加しました。"),
    "remove_truck": ("Remove truck", "車両を削除"),
    "remove_from": ("Remove from", "削除する対策"),
    "confirm_remove_truck": ("I understand the truck's records are removed from these countermeasures (history is kept).",
                             "選択した対策から車両の記録が削除されることを理解しました（履歴は残ります）。"),
    "truck_removed": ("{fleet} removed.", "{fleet}を削除しました。"),
    "na_tip": ("To exclude a truck from one countermeasure without deleting it, tick N/A in the Progress tab.",
               "削除せずに対象外にする場合は、進捗入力タブで「対象外」をチェックしてください。"),
    "downloads": ("Downloads", "ダウンロード"),
    "dl_excel": ("Excel workbook", "Excelブック"),
    "dl_pdf": ("Action plan (PDF)", "実行計画（PDF）"),
    "dl_csv": ("Truck records (CSV)", "車両記録（CSV）"),
    "publish": ("Publish to the data folder", "データフォルダに公開"),
    "publish_help": ("Saves today's Excel and PDF in reports/ so everyone keeps the same version.",
                     "本日のExcelとPDFをreports/に保存し、全員が同じ版を参照できるようにします。"),
    "publish_btn": ("Publish reports", "レポートを公開"),
    "published": ("Published in {where}", "{where}に公開しました"),
    "settings": ("Settings", "設定"),
    "set_tz": ("Project time zone", "プロジェクトのタイムゾーン"),
    "set_tz_help": ("Defines «today». Example: Africa/Lusaka, America/Bogota, Asia/Tokyo.",
                    "「本日」の基準です。例：Africa/Lusaka、America/Bogota、Asia/Tokyo。"),
    "set_due_soon": ("Warn … days before the fleet target", "フリート目標日の何日前から警告"),
    "set_due_soon_help": ("Calendar days.", "暦日数。"),
    "save_settings": ("Save settings", "設定を保存"),
    "settings_saved": ("Settings saved.", "設定を保存しました。"),
    "err_settings": ("Invalid values: {items}", "無効な値：{items}"),
    "data_location": ("Data stored in: {where}", "データ保存先：{where}"),
}

LANG_INDEX = {"en": 0, "ja": 1}


def translator(lang: str) -> Callable[..., str]:
    i = LANG_INDEX.get(lang, 0)

    def t(key: str, **kwargs) -> str:
        pair = TEXTS.get(key)
        text = pair[i] if pair else key
        if kwargs:
            try:
                return text.format(**kwargs)
            except (KeyError, ValueError, IndexError):
                return text
        return text

    return t
