# VERSIONE: 2.3.2 (RIPRISTINO TOTALE - Date, Isole di Tempo e Tabelle Annuali)
import streamlit as st
import pandas as pd
import datetime
import requests
from io import StringIO

# --- CONFIGURAZIONE E COSTANTI ---
DRIVE_URL = "https://drive.google.com/uc?export=download&id=1n4b33BgWxIUDWm4xuDnhjICPkqGWi2po"

# --- FUNZIONI DI SUPPORTO ---

def get_fascia_info(ora_str):
    """Assegna l'ora a una delle 4 fasce personalizzate"""
    try:
        h = int(ora_str.split(":")[0])
        m = int(ora_str.split(":")[1])
        t = h + m/60
        # Definizione intervalli larghi per non perdere dati
        if t < 12.25: return 0, "09:00-12:00"
        elif 12.25 <= t < 15.75: return 1, "12:30-15:30"
        elif 15.75 <= t < 19.25: return 2, "16:00-19:00"
        else: return 3, "19:30-22:00"
    except: return 0, "09:00-12:00"

@st.cache_data(ttl=3600)
def load_data_from_drive(url):
    try:
        r = requests.get(url)
        return r.text if r.status_code == 200 else None
    except: return None

def parse_ics(content):
    if not content: return []
    data = []
    lines = StringIO(content).readlines()
    current_event = {}
    in_event = False
    for line in lines:
        line = line.strip()
        if line.startswith("BEGIN:VEVENT"):
            in_event = True
            current_event = {"summary": "", "description": "", "dtstart": ""}
        elif line.startswith("END:VEVENT"):
            in_event = False
            txt = (current_event["summary"] + " " + current_event["description"]).lower()
            if "nominativo" in txt and "codice fiscale" in txt:
                raw_dt = current_event["dtstart"].split(":")[-1]
                if len(raw_dt) >= 8:
                    try:
                        dt = datetime.datetime.strptime(raw_dt[:15], "%Y%m%dT%H%M%S")
                        dt += datetime.timedelta(hours=(2 if 3 < dt.month < 10 else 1))
                        ora_f = dt.strftime("%H:%M")
                        f_idx, f_lbl = get_fascia_info(ora_f)
                        data.append({
                            "Data": dt.date(), "Anno": dt.year, "Settimana": dt.isocalendar()[1], 
                            "Giorno": dt.weekday(), "Ora_Esatta": ora_f, "Fascia": f_lbl
                        })
                    except: continue
        elif in_event:
            if line.startswith("DTSTART"): current_event["dtstart"] = line
            elif line.startswith("SUMMARY:"): current_event["summary"] = line[8:]
            elif "Nominativo" in line or "Codice fiscale" in line: current_event["description"] += line
    return data

# --- CSS E LAYOUT ---
st.set_page_config(page_title="Dashboard Appuntamenti 2.3.2", layout="wide")
st.markdown("""
<style>
    thead tr th:first-child {display:none} tbody th {display:none}
    .year-card { border: 1px solid #dcdde1; border-radius: 12px; padding: 15px; background-color: #ffffff; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    .grid-table { width: 100%; border-collapse: separate; border-spacing: 2px; table-layout: fixed; }
    .grid-table td { border-bottom: 1px solid #f1f2f6; padding: 8px 2px; vertical-align: middle; height: 50px; border-radius: 4px; text-align: center; }
    .day-label { width: 22%; font-weight: bold; font-size: 11px; color: #7f8c8d; text-transform: uppercase; text-align: left !important; }
    .time-slot { width: 19.5%; font-size: 12px; font-weight: bold; }
    .free-slot { background-color: #d1dce5; color: #d1dce5; border: 1px solid #b8c5d1; }
    .busy-slot { background-color: #ffffff; border: 1px solid #e1e8ed; color: #2980b9; }
    .insight-box { background-color: #f1f8ff; border-left: 5px solid #007bff; padding: 20px; border-radius: 10px; margin-bottom: 25px; color: #004085; }
    @media (max-width: 768px) { [data-testid="stHorizontalBlock"] { flex-direction: column !important; } }
</style>
""", unsafe_allow_html=True)

st.title("📊 Analisi Carico di Lavoro PRO")

content = load_data_from_drive(DRIVE_URL)
raw_data = parse_ics(content) if content else []

if raw_data:
    df = pd.DataFrame(raw_data)
    mesi_it = {1:"Gennaio", 2:"Febbraio", 3:"Marzo", 4:"Aprile", 5:"Maggio", 6:"Giugno", 7:"Luglio", 8:"Agosto", 9:"Settembre", 10:"Ottobre", 11:"Novembre", 12:"Dicembre"}
    g_abr = {0:"Lun", 1:"Mar", 2:"Mer", 3:"Gio", 4:"Ven", 5:"Sab"}
    
    # SELETTORE SETTIMANA E DATE
    c_sel, c_info = st.columns([1, 2])
    with c_sel:
        sel_week = st.number_input("Settimana:", 1, 53, datetime.date.today().isocalendar()[1])
    
    # Calcolo date inizio/fine settimana
    oggi = datetime.date.today()
    ref_start = datetime.date.fromisocalendar(oggi.year, sel_week, 1)
    ref_end = datetime.date.fromisocalendar(oggi.year, sel_week, 7)
    c_info.info(f"📅 **Riferimento Settimana {sel_week}:** dal {ref_start.day} {mesi_it[ref_start.month]} al {ref_end.day} {mesi_it[ref_end.month]}")

    df_week = df[df["Settimana"] == sel_week]
    
    if not df_week.empty:
        # --- ANALISI ISOLE DI TEMPO ---
        num_anni = df_week["Anno"].nunique()
        media_app = round(len(df_week) / num_anni, 1)
        fasce_possibili = ["09:00-12:00", "12:30-15:30", "16:00-19:00", "19:30-22:00"]
        counts = df_week['Fascia'].value_counts()
        piu_libera = min(fasce_possibili, key=lambda x: counts.get(x, 0))
        piu_carica = max(fasce_possibili, key=lambda x: counts.get(x, 0))
        
        st.markdown(f"""
        <div class='insight-box'>
            <h3 style='margin-top:0;'>💡 Analisi Predittiva Settimana {sel_week}</h3>
            • <b>Frequenza Media:</b> In questa settimana hai mediamente <b>{media_app}</b> appuntamenti.<br>
            • <b>Isola di tempo:</b> Storicamente la tua fascia più libera è <b>{piu_libera}</b>.<br>
            • <b>Momento critico:</b> La fascia solitamente più impegnata è <b>{piu_carica}</b>.<br>
            <small>Basato su uno storico di {num_anni} anni.</small>
        </div>
        """, unsafe_allow_html=True)

        # --- TABELLE ANNUALI (2024, 2025, ecc.) ---
        anni = sorted(df_week["Anno"].unique()) 
        cols = st.columns(len(anni))
        for idx, anno in enumerate(anni):
            with cols[idx]:
                df_anno = df_week[df_week["Anno"] == anno]
                rows_html = ""
                for g_idx in range(6): 
                    ev_g = df_anno[df_anno["Giorno"] == g_idx]
                    corsie = ["", "", "", ""]
                    for _, row in ev_g.sort_values("Ora_Esatta").iterrows():
                        c_idx, _ = get_fascia_info(row["Ora_Esatta"])
                        corsie[c_idx] += f"<div>{row['Ora_Esatta']}</div>"
                    
                    cls = ["time-slot " + ("busy-slot" if c else "free-slot") for c in corsie]
                    rows_html += f"""
                    <tr>
                        <td class='day-label'>{g_abr[g_idx]} ({len(ev_g)})</td>
                        <td class='{cls[0]}'>{corsie[0]}</td>
                        <td class='{cls[1]}'>{corsie[1]}</td>
                        <td class='{cls[2]}'>{corsie[2]}</td>
                        <td class='{cls[3]}'>{corsie[3]}</td>
                    </tr>"""
                
                st.markdown(f"""
                <div class='year-card'>
                    <h3 style='text-align:center;'>{anno}</h3>
                    <table class='grid-table'>
                        <tr style='font-size:8px; color:#95a5a6;'>
                            <th>Giorno</th><th>09-12</th><th>12:3-15</th><th>16-19</th><th>19:3-22</th>
                        </tr>
                        {rows_html}
                    </table>
                </div>""", unsafe_allow_html=True)

    # --- MAPPA ORARIA FREQUENZE (BLU) ---
    st.markdown("---")
    st.subheader("📊 Mappa Oraria delle Frequenze")
    ordine_f = ["09:00-12:00", "12:30-15:30", "16:00-19:00", "19:30-22:00"]
    pivot_f = df.pivot_table(index="Giorno", columns="Fascia", values="Anno", aggfunc='count', fill_value=0)
    pivot_f.index = pivot_f.index.map(g_abr)
    pivot_f = pivot_f.reindex(index=["Lun","Mar","Mer","Gio","Ven","Sab"], columns=ordine_f).fillna(0).astype(int)
    st.dataframe(pivot_f.style.background_gradient(cmap="Blues", axis=None).format("{:.0f}"), use_container_width=True)

    # --- TREND MENSILE (ROSSO) ---
    st.subheader("📈 Trend di Carico Mensile")
    df["Mese_T"] = df["Data"].apply(lambda x: mesi_it[x.month])
    pivot_m = df.pivot_table(index="Mese_T", columns="Anno", values="Giorno", aggfunc="count", fill_value=0)
    pivot_m = pivot_m.reindex([mesi_it[m] for m in range(1,13) if mesi_it[m] in pivot_m.index])
    st.dataframe(pivot_m.style.background_gradient(cmap="Reds").format("{:.0f}"), use_container_width=True)
else:
    st.warning("⚠️ Caricamento dati da Google Drive fallito o file vuoto.")
