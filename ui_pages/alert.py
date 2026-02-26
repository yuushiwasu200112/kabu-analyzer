if page == "アラート":
    st.title("🔔 アラート設定")
    st.caption("銘柄の条件を設定して、条件達成時に通知を受け取れます")

    # セッション初期化
    if "alerts" not in st.session_state:
        st.session_state.alerts = []
    if "alert_history" not in st.session_state:
        st.session_state.alert_history = []

    # アラート追加
    st.subheader("➕ 新しいアラートを作成")
    al_col1, al_col2, al_col3, al_col4 = st.columns([2, 2, 2, 1])
    with al_col1:
        al_code = st.text_input("証券コード", max_chars=4, key="al_code", placeholder="例: 7203")
    with al_col2:
        al_type = st.selectbox("条件タイプ", [
            "総合スコアが○点以上", "総合スコアが○点以下",
            "収益性が○点以上", "安全性が○点以上",
            "成長性が○点以上", "割安度が○点以上",
            "ROEが○%以上", "PERが○倍以下",
            "配当利回りが○%以上",
        ], key="al_type")
    with al_col3:
        al_value = st.number_input("しきい値", min_value=0.0, value=70.0, step=5.0, key="al_value")
    with al_col4:
        st.write("")
        st.write("")
        if st.button("🔔 追加", type="primary", key="al_add"):
            if al_code and len(al_code) == 4 and al_code in CODE_MAP:
                alert = {
                    "code": al_code,
                    "name": CODE_MAP[al_code]["name"],
                    "type": al_type,
                    "value": al_value,
                    "active": True,
                    "created": datetime.datetime.now().strftime("%Y-%m-%d %H:%M") if "datetime" in dir() else "now",
                }
                st.session_state.alerts.append(alert)
                st.success(f"✅ {CODE_MAP[al_code]['name']} のアラートを設定しました")
            elif al_code:
                st.error("❌ 未対応の証券コードです")

    # アラート一覧
    if st.session_state.alerts:
        st.divider()
        st.subheader("📋 設定中のアラート")

        for i, alert in enumerate(st.session_state.alerts):
            acol1, acol2, acol3, acol4 = st.columns([2, 3, 2, 1])
            with acol1:
                status = "🟢" if alert["active"] else "⏸️"
                st.markdown(f"{status} **{alert['code']}** {alert['name'][:8]}")
            with acol2:
                st.markdown(f"{alert['type']}（{alert['value']}）")
            with acol3:
                if alert["active"]:
                    if st.button("⏸️ 停止", key=f"al_pause_{i}"):
                        st.session_state.alerts[i]["active"] = False
                        st.rerun()
                else:
                    if st.button("▶️ 再開", key=f"al_resume_{i}"):
                        st.session_state.alerts[i]["active"] = True
                        st.rerun()
            with acol4:
                if st.button("🗑️", key=f"al_del_{i}"):
                    st.session_state.alerts.pop(i)
                    st.rerun()

        # アラートチェック実行
        st.divider()
        if st.button("🔍 アラートを今すぐチェック", type="primary"):
            API_KEY = os.getenv("EDINET_API_KEY")
            active_alerts = [a for a in st.session_state.alerts if a["active"]]
            triggered = []

            progress = st.progress(0, text="チェック中...")
            codes_to_check = list(set(a["code"] for a in active_alerts))
            results_cache = {}

            for idx, code in enumerate(codes_to_check):
                progress.progress((idx + 1) / len(codes_to_check), text=f"{CODE_MAP[code]['name']} をチェック中...")
                try:
                    r = analyze_company(code, API_KEY)
                    if r:
                        results_cache[code] = r
                except:
                    continue
            progress.empty()

            for alert in active_alerts:
                r = results_cache.get(alert["code"])
                if not r:
                    continue

                score = r["score"]["total_score"]
                cats = r["score"]["category_scores"]
                inds = r["indicators"]
                val = alert["value"]
                met = False
                actual = 0

                if "総合スコアが" in alert["type"] and "以上" in alert["type"]:
                    met = score >= val
                    actual = score
                elif "総合スコアが" in alert["type"] and "以下" in alert["type"]:
                    met = score <= val
                    actual = score
                elif "収益性が" in alert["type"]:
                    actual = cats.get("収益性", 0)
                    met = actual >= val
                elif "安全性が" in alert["type"]:
                    actual = cats.get("安全性", 0)
                    met = actual >= val
                elif "成長性が" in alert["type"]:
                    actual = cats.get("成長性", 0)
                    met = actual >= val
                elif "割安度が" in alert["type"]:
                    actual = cats.get("割安度", 0)
                    met = actual >= val
                elif "ROEが" in alert["type"]:
                    actual = inds.get("ROE", 0)
                    met = actual >= val
                elif "PERが" in alert["type"] and "以下" in alert["type"]:
                    actual = inds.get("PER", 999)
                    met = actual <= val and actual > 0
                elif "配当利回りが" in alert["type"]:
                    actual = inds.get("配当利回り", 0)
                    met = actual >= val

                if met:
                    triggered.append({
                        "code": alert["code"],
                        "name": alert["name"],
                        "type": alert["type"],
                        "threshold": val,
                        "actual": actual,
                        "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M") if "datetime" in dir() else "now",
                    })

            if triggered:
                st.subheader("🚨 アラート発動！")
                for t in triggered:
                    st.success(f"🔔 **{t['name']}（{t['code']}）**: {t['type']}（設定値: {t['threshold']} → 実績値: {t['actual']:.2f}）")
                    st.session_state.alert_history.append(t)
            else:
                st.info("📌 条件を満たすアラートはありませんでした")

    # アラート履歴
    if st.session_state.alert_history:
        st.divider()
        st.subheader("📜 アラート履歴")
        for h in reversed(st.session_state.alert_history[-10:]):
            st.caption(f"🔔 {h.get('time','')} | {h['name']}（{h['code']}）: {h['type']} → {h['actual']:.2f}")

    if not st.session_state.alerts:
        st.info("📌 アラートを設定すると、条件達成時に通知を受け取れます")

    st.divider()
    st.caption("⚠️ 本ツールは投資助言ではありません。")
    st.stop()

# ========================================
# セクター分析ページ
# ========================================
