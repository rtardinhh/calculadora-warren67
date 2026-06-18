import streamlit as st
import math
import json
import os
from datetime import datetime
from PIL import Image

# Configuración de la página
st.set_page_config(page_title="Calculadora Puente Warren - UNICA", layout="centered")

# Inicializar estado de la sesión
if 'ingresado' not in st.session_state:
    st.session_state.ingresado = False
if 'history' not in st.session_state:
    st.session_state.history = []

# ============================
# PANTALLA DE HOME (INICIO)
# ============================
if not st.session_state.ingresado:
    # Logo de la Universidad en la esquina superior derecha
    try:
        logo_uni = Image.open("logo.png")
        col_izq, col_der = st.columns([4, 1])
        with col_der:
            st.image(logo_uni, width=100)
    except:
        pass

    st.markdown("<h1 style='text-align: center;'>Proyecto Integrador</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center;'>Análisis Estructural: Armaduras Warren</h3>", unsafe_allow_html=True)
    st.markdown("---")

    # Imagen generada por Gemini arriba del botón
    try:
        img_gemini = Image.open("Gemini_Generated_Image_eui7skeui7skeui7.png")
        st.image(img_gemini, use_container_width=True)
    except:
        st.warning("Asegúrate de subir la imagen de Gemini con el nombre correcto.")

    st.write("##")
    if st.button("INGRESAR A LA CALCULADORA", use_container_width=True):
        st.session_state.ingresado = True
        st.rerun()

# ============================
# PANTALLA DE LA CALCULADORA
# ============================
else:
    # Header con logo pequeño
    try:
        logo_uni = Image.open("logo.png")
        st.sidebar.image(logo_uni, width=80)
    except:
        pass

    st.sidebar.button("⬅️ Volver al Inicio", on_click=lambda: st.session_state.update(ingresado=False))
    st.title("🏗️ Calculadora de Armadura Tipo Warren")
    st.markdown("---")

    # --- MOTOR DE CÁLCULO (Completo) ---
    class WarrenTruss:
        def __init__(self, L, H, panels, P_total):
            self.L = L
            self.H = H
            self.panels = panels
            self.P_total = P_total
            self.results = {}
            self._analyze()

        def _analyze(self):
            L, H, n, Pt = self.L, self.H, self.panels, self.P_total
            d = L / n
            diag_len = math.hypot(d, H)
            sin_a = H / diag_len if diag_len != 0 else 0
            angle_deg = math.degrees(math.atan2(H, d))
            load_nodes = max(1, n - 1)
            P_node = Pt / load_nodes
            Ra = Rb = Pt / 2

            V, shear = [], Ra
            for i in range(n):
                V.append(shear)
                if i < load_nodes:
                    shear -= P_node

            bot_forces = []
            for i in range(n):
                x_right = (i + 1) * d
                M = Ra * x_right
                if i > 0:
                    for j in range(1, i + 1):
                        M -= P_node * (j * d)
                bot_forces.append(M / H if H != 0 else 0)

            top_forces = []
            for i in range(n):
                x_mid = (i + 0.5) * d
                M = Ra * x_mid - sum(
                    P_node * (j * d) for j in range(1, i + 1) if j * d < x_mid
                )
                top_forces.append(-M / H if H != 0 else 0)

            diag_forces = [V[i] / sin_a if sin_a != 0 else 0 for i in range(n)]

            members = []
            for i, f in enumerate(top_forces):
                members.append({
                    "id": f"CS{i+1}",
                    "name": f"Cordon Superior {i+1}",
                    "type": "top_chord",
                    "force": round(f, 3),
                    "length": round(d, 3),
                    "stress_type": "Compresión" if f < 0 else "Tensión"
                })
            for i, f in enumerate(bot_forces):
                members.append({
                    "id": f"CI{i+1}",
                    "name": f"Cordon Inferior {i+1}",
                    "type": "bot_chord",
                    "force": round(f, 3),
                    "length": round(d, 3),
                    "stress_type": "Tensión" if f > 0 else "Compresión"
                })
            for i, f in enumerate(diag_forces):
                members.append({
                    "id": f"D{i+1}",
                    "name": f"Diagonal {i+1}",
                    "type": "diagonal",
                    "force": round(f, 3),
                    "length": round(diag_len, 3),
                    "stress_type": "Tensión" if f > 0 else "Compresión"
                })

            self.results = {
                "L": L, "H": H, "panels": n,
                "P_total": Pt, "P_node": round(P_node, 3),
                "Ra": round(Ra, 3), "Rb": round(Rb, 3),
                "d": round(d, 3), "diag": round(diag_len, 3),
                "angle_deg": round(angle_deg, 2),
                "members": members,
                "max_force": round(max(abs(m["force"]) for m in members), 3),
                "n_members": len(members),
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }

        def evaluate_safety(self, material="Acero A36", A_cm2=50.0):
            A_mm2 = A_cm2 * 100.0
            MATERIALS = {
                "Acero A36": {"Fy": 250.0},
                "Acero A572": {"Fy": 345.0},
                "Aluminio 6061": {"Fy": 276.0},
            }
            Fy_MPa = MATERIALS.get(material, MATERIALS["Acero A36"])["Fy"]
            allowable_MPa = Fy_MPa / 1.67

            member_evals, critical, warnings = [], [], []
            for m in self.results["members"]:
                F_N = abs(m["force"]) * 1000.0
                sigma_MPa = F_N / A_mm2 if A_mm2 != 0 else float('inf')
                ratio = sigma_MPa / allowable_MPa if allowable_MPa != 0 else float('inf')

                if ratio > 1.0:
                    status, color = "FALLA", "danger"
                    critical.append(m["id"])
                elif ratio > 0.85:
                    status, color = "LIMITE", "warn"
                    warnings.append(m["id"])
                else:
                    status, color = "SEGURO", "safe"

                member_evals.append({
                    **m,
                    "sigma_MPa": round(sigma_MPa, 2),
                    "allowable_MPa": round(allowable_MPa, 2),
                    "ratio": round(ratio, 3),
                    "status": status, "color": color
                })

            if critical:
                verdict, v_level = "PELIGROSO", "danger"
            elif warnings:
                verdict, v_level = "PRECAUCIÓN", "warn"
            else:
                verdict, v_level = "SEGURO", "safe"

            sugg = []
            hl = self.results["H"] / self.results["L"] if self.results["L"] != 0 else 0
            if critical:
                F_max_N = self.results["max_force"] * 1000.0
                A_min_mm2 = (F_max_N / allowable_MPa) * 1.15 if allowable_MPa != 0 else A_mm2 * 2
                A_min_cm2 = A_min_mm2 / 100.0
                sugg.append(f"Aumentar sección transversal a mínimo {A_min_cm2:.2f} cm²")
                sugg.append("Considerar material de mayor resistencia (mayor Fy)")
                if self.results["panels"] < 8:
                    sugg.append("Aumentar número de paneles para reducir fuerzas por miembro")
                if hl < 0.10:
                    sugg.append("Aumentar altura del puente (relación H/L >= 0.10 recomendada)")
                if material != "Acero A572":
                    sugg.append("Cambiar a Acero A572 (mayor resistencia que A36)")
            elif warnings:
                sugg.append("Miembros cercanos al límite — revisar cargas de servicio")
                A_sug_cm2 = (A_mm2 * 1.175) / 100.0
                sugg.append(f"Aumentar sección en 15-20% (aprox. {A_sug_cm2:.2f} cm²)")
            else:
                sugg.append("Diseño dentro de parámetros admisibles")
                if evals:
                    max_r = max(e["ratio"] for e in evals)
                    A_opt_mm2 = A_mm2 * max_r * 1.10
                    if A_opt_mm2 < A_mm2 * 0.80:
                        A_opt_cm2 = A_opt_mm2 / 100.0
                        sugg.append(f"Podría optimizar la sección a ~{A_opt_cm2:.2f} cm²")

            if hl < 0.08:
                sugg.append(f"Relación H/L = {hl:.2f} muy baja — riesgo de pandeo lateral")
            elif hl > 0.20:
                sugg.append(f"Relación H/L = {hl:.2f} elevada — revisar cargas de viento")

            return {
                "verdict": verdict, "v_level": v_level, "material": material,
                "section_area_cm2": round(A_cm2, 1),
                "Fy_MPa": round(Fy_MPa, 0),
                "allowable_MPa": round(allowable_MPa, 1),
                "critical_members": critical, "warning_members": warnings,
                "member_evals": member_evals, "suggestions": sugg
            }

    # --- INTERFAZ STREAMLIT ---
    st.sidebar.header("📋 Parámetros de Entrada")

    with st.sidebar.form("params_form"):
        L = st.number_input("Longitud total L (m)", min_value=1.0, value=20.0, step=1.0)
        H = st.number_input("Altura H (m)", min_value=0.5, value=3.0, step=0.5)
        n = st.slider("Número de paneles", 2, 20, 6)
        P = st.number_input("Carga total P (kN)", min_value=1.0, value=500.0, step=10.0)
        A_cm2 = st.number_input("Área de sección (cm²)", min_value=1.0, value=50.0, step=5.0)
        mat = st.selectbox("Material", ["Acero A36", "Acero A572", "Aluminio 6061"])
        submit = st.form_submit_button("CALCULAR", use_container_width=True)

    # Tabs para organizar resultados
    tab1, tab2, tab3 = st.tabs(["📊 Resumen", "📋 Tabla de Miembros", "📈 Diagrama"])

    if submit:
        truss = WarrenTruss(L, H, n, P)
        safety = truss.evaluate_safety(material=mat, A_cm2=A_cm2)
        res = truss.results

        # Guardar en historial
        st.session_state.history.append({
            "timestamp": res["timestamp"],
            "L": L, "H": H, "panels": n, "P": P,
            "area": A_cm2, "material": mat,
            "verdict": safety["verdict"]
        })

        sigma_max = max(e["sigma_MPa"] for e in safety["member_evals"])

        # --- TAB 1: RESUMEN ---
        with tab1:
            col_map = {"safe": "✅", "warn": "⚠️", "danger": "❌"}
            v_emoji = col_map[safety["v_level"]]

            if safety["v_level"] == "danger":
                st.error(f"{v_emoji} ESTADO: {safety['verdict']}")
            elif safety["v_level"] == "warn":
                st.warning(f"{v_emoji} ESTADO: {safety['verdict']}")
            else:
                st.success(f"{v_emoji} ESTADO: {safety['verdict']}")

            st.caption(f"Material: {mat} | σ_adm = {safety['allowable_MPa']} MPa | Área = {safety['section_area_cm2']} cm²")

            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("Ra = Rb", f"{res['Ra']:.1f} kN")
            c2.metric("Fuerza Máx.", f"{res['max_force']:.1f} kN")
            c3.metric("Tensión Máx.", f"{sigma_max:.1f} MPa")
            c4.metric("N° Miembros", res["n_members"])
            c5.metric("Áng. Diagonal", f"{res['angle_deg']:.1f}°")

            st.subheader("💡 Sugerencias de Diseño")
            for s in safety["suggestions"]:
                st.info(s)

        # --- TAB 2: TABLA DE MIEMBROS ---
        with tab2:
            import pandas as pd
            df = pd.DataFrame(safety["member_evals"])
            df_display = df[["id", "name", "stress_type", "force", "length", 
                           "sigma_MPa", "allowable_MPa", "ratio", "status"]]

            def highlight_status(val):
                if val == "FALLA": return 'background-color: #FEE2E2; color: #DC2626'
                if val == "LIMITE": return 'background-color: #FEF3C7; color: #D97706'
                if val == "SEGURO": return 'background-color: #DCFCE7; color: #16A34A'
                return ''

            st.dataframe(df_display.style.applymap(highlight_status, subset=["status"]),
                        use_container_width=True, height=400)

            n_s = sum(1 for e in safety["member_evals"] if e["color"] == "safe")
            n_w = sum(1 for e in safety["member_evals"] if e["color"] == "warn")
            n_d = sum(1 for e in safety["member_evals"] if e["color"] == "danger")
            st.caption(f"Total: {res['n_members']} miembros | Seguros: {n_s} | Límite: {n_w} | Falla: {n_d}")

        # --- TAB 3: DIAGRAMA (Simplificado) ---
        with tab3:
            import matplotlib.pyplot as plt
            import matplotlib.patches as patches

            fig, ax = plt.subplots(figsize=(10, 4))
            d = res["d"]
            Ht = res["H"]

            # Cordón inferior
            ax.plot([0, L], [0, 0], 'b-', linewidth=3, label='Cordon Inferior')
            # Cordón superior
            ax.plot([0, L], [Ht, Ht], 'r-', linewidth=3, label='Cordon Superior')
            # Diagonales
            for i in range(n):
                if i % 2 == 0:
                    ax.plot([i*d, (i+1)*d], [0, Ht], 'g-', linewidth=2, alpha=0.7)
                else:
                    ax.plot([i*d, (i+1)*d], [Ht, 0], 'g-', linewidth=2, alpha=0.7)
            # Nodos
            for i in range(n+1):
                ax.plot(i*d, 0, 'bo', markersize=8)
                ax.plot(i*d, Ht, 'ro', markersize=8)
            # Apoyos
            ax.plot([0, 0], [0, -0.5], 'k-', linewidth=4)
            ax.plot([L, L], [0, -0.5], 'k-', linewidth=4)
            ax.plot([-0.5, L+0.5], [-0.5, -0.5], 'k-', linewidth=2)

            ax.set_xlim(-2, L+2)
            ax.set_ylim(-1, Ht+2)
            ax.set_aspect('equal')
            ax.set_title(f"Diagrama de Armadura Warren ({n} paneles)")
            ax.legend(loc='upper right')
            ax.axis('off')

            st.pyplot(fig)
            st.caption("🟢 Tensión | 🔴 Compresión | Azul: Nodos inferiores | Rojo: Nodos superiores")

    else:
        with tab1:
            st.info("💡 Completa los parámetros en el menú lateral y presiona CALCULAR para ver los resultados.")
        with tab2:
            st.info("Los datos de los miembros aparecerán aquí después de calcular.")
        with tab3:
            st.info("El diagrama de la armadura se mostrará aquí.")

    # Historial
    if st.session_state.history:
        with st.sidebar.expander("📜 Historial de Cálculos"):
            for i, h in enumerate(reversed(st.session_state.history[-5:])):
                st.caption(f"{h['timestamp']} | {h['L']}m x {h['H']}m | {h['material']} | {h['verdict']}")
