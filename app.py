# VERSIONE: 2.2 (Stabile - Analisi Fasce Orarie + Ripristino Mappa Oraria)
import streamlit as st
import pandas as pd
import datetime
import requests
from io import StringIO

# --- CONFIGURAZIONE E COSTANTI ---
DRIVE_URL = "https://drive.google.com/uc?export=download&id=1n4b33BgWxIUDWm4xuDnhjICPkqGWi2po"

# --- FUNZIONI DI SUPPORTO ---

def calcola_pasqua(anno):
    a, b, c = anno % 19, anno // 100, anno % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mese = (h + l - 7 * m + 114) // 31
    giorno = ((h + l - 7 * m + 114) % 31) + 1
    pasqua = datetime.date(anno, mese, giorno)
    return pasqua, pasqua + datetime.timedelta(days=1)

def get_festivita(anno):
    p, pp = calcola_pasqua(anno)
    return {datetime.date(anno,1,1):"Capodanno", datetime.date(anno,1,6):"Epifania", 
            datetime.date(anno,4,25):"Liberazione", datetime.date(anno,5,1):"1 Maggio", 
            datetime.date(anno,6,2):"Repubblica", datetime.date(anno,8,15):"Ferragosto", 
            datetime.date(anno,11,1):"Ognissanti", datetime.date(anno,12,8):"Immacolata", 
            datetime.date(anno,12,25):"Natale", datetime.date(anno,12,26):"S. Stefano", p:"Pasqua", pp:"Pasquetta"}

def assegna_corsia(ora_str):
    try:
        h = int(ora_str.split(":")[0])
        m = int(ora_str.split(":")[1])
        t = h + m/60
        if t <= 11.75: return 0    
        elif 12.0 <= t <= 17.25: return 1 
        else: return 2                 
    except: return 1

def get_fascia_label(hour):
    if hour < 9: return "08:00-09:00"
    elif 9 <= hour < 11: return "09:00-11:00"
    elif 11 <= hour < 13: return "11:00-13:00"
    elif 13 <= hour < 15: return "13:00-15:00"
    elif 15 <= hour < 17: return "15:00-17:00"
    elif 17 <= hour < 19: return "17:00-19:00"
    else: return "19:00-22:00"

@st.cache_data(ttl=3600)
def load_data_from_drive(url):
    try:
        r = requests.get(url)
        return r.text if r.status_code == 200 else None
    except: return None

def parse_ics(content):
    if not content: return []
    data = []
    current_event = {"summary": "", "description": "", "dtstart": ""}
    in_event = False
    for line in StringIO(content):
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
                        data.append({"Data": dt.date(), "Anno": dt.year, "Settimana": dt.isocalendar()[1], 
                                     "Giorno": dt.weekday(), "Ora_Esatta": dt.strftime("%H:%M"), 
                                     "Ora_Num": dt.hour, "Fascia": get_fascia_label(dt.hour)})
                    except: continue
        elif in_event:
            if line.startswith("DTSTART"): current_event["dtstart"] = line
            elif line.startswith("SUMMARY:"): current_event["summary"] = line[8:]
            elif "Nominativo" in line or "Codice fiscale" in line: current_event["description"] += line
    return data

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Dashboard Appuntamenti PRO", layout="wide")
st.markdown("""
<style>
    thead tr th:first-child {display:none} tbody th {display:none}
    div[data-testid="stNumberInput"] input { font-size: 24px !important; font-weight: bold; color: #c0392b; text-align: center; }
    .year-card { border: 1px solid #dcdde1; border-radius: 12px; padding: 15px; background-color: #ffffff; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 20px; }
    .grid-table { width: 100%; border-collapse: separate; border-spacing: 2px; table-layout: fixed; }
    .grid-table td { border-bottom: 1px solid #f1f2f6; padding: 8px 2px; vertical-align: middle; height: 50px; border-radius: 4px; }
    .day-label { width: 22%; font-weight: bold; font-size: 11px; color: #7f8c8d; text-transform: uppercase; background-color: white !important; }
    .time-slot { width: 26%; text-align: center; font-size: 13px; color: #2c3e50; font-weight: bold; line-height: 1.1; }
    .free-slot { background-color: #d1dce5; border: 1px solid #b8c5d1; }
    .busy-slot { background-color: #ffffff; border: 1px solid #e1e8ed; color: #2980b9; }
    .holiday-label { display: block; font-size: 9px; color: #e67e22; font-weight: normal; }
    .insight-box { background-color: #f8f9fa; border-left: 5px solid #2980b9; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
    @media (max-width: 768px) { [data-testid="stHorizontalBlock"] { flex-direction: column !important; } }
</style>
""", unsafe_allow_html=True)

st.title("📊 Carico di Lavoro Storico")

content = load_data_from_drive(DRIVE_URL)
raw_data = parse_ics(content) if content else []

if raw_data:
    df = pd.DataFrame(raw_data)
    mesi_it = {1:"Gennaio", 2:"Febbraio", 3:"Marzo", 4:"Aprile", 5:"Maggio", 6:"Giugno", 7:"Luglio", 8:"Agosto", 9:"Settembre", 10:"Ottobre", 11:"Novembre", 12:"Dicembre"}
    g_comp = {0:"Lunedì", 1:"Martedì", 2:"Mercoledì", 3:"Giovedì", 4:"Venerdì", 5:"Sabato"}
    g_abr = {0:"Lun", 1:"Mar", 2:"Mer", 3:"Gio", 4:"Ven", 5:"Sab"}
    
    oggi = datetime.date.today()
    sel_week = st.number_input("Settimana:", 1, 53, oggi.isocalendar()[1])
    df_week = df[df["Settimana"] == sel_week]
    
    if not df_week.empty:
        # --- NUOVA ANALISI DELLE FASCE ---
        # Calcoliamo quale fascia è storicamente più scarica (Morning vs Afternoon vs Evening)
        # Dividiamo i dati in 3 macro-fasce per l'insight
        df_week['MacroFascia'] = df_week['Ora_Num'].apply(lambda x: "Mattina" if x < 12 else ("Pomeriggio" if x < 17 else "Sera"))
        fascia_stats = df_week['MacroFascia'].value_counts()
        piu_carico_macro = fascia_stats.idxmax()
        piu_libero_macro = "Mattina" if "Mattina" not in fascia_stats else ("Pomeriggio" if "Pomeriggio" not in fascia_stats else ("Sera" if "Sera" not in fascia_stats else fascia_stats.idxmin()))
        
        st.markdown(f"""
        <div class='insight-box'>
            <b>💡 Analisi del Carico Storico (Settimana {sel_week}):</b><br>
            • <b>Momento ideale per te:</b> Storicamente la <b>{piu_libero_macro}</b> è la fascia più scarica.<br>
            • <b>Ritmo di lavoro:</b> Il carico maggiore si concentra prevalentemente nel <b>{piu_carico_macro}</b>.<br>
            • <b>Nota:</b> In questa settimana hai avuto un totale di {len(df_week)} appuntamenti distribuiti negli anni.
        </div>
        """, unsafe_allow_html=True)

        # --- TABELLE ANNUALI ---
        anni = sorted(df_week["Anno"].unique()) 
        cols = st.columns(len(anni))
        for idx, anno in enumerate(anni):
            with cols[idx]:
                df_anno = df_week[df_week["Anno"] == anno]
                feste = get_festivita(anno)
                rows_html = ""
                for g_idx in range(6): 
                    data_p = datetime.date.fromisocalendar(anno, sel_week, g_idx+1)
                    festa_n = feste.get(data_p, "")
                    f_lbl = f"<span class='holiday-label'>{festa_n}</span>" if festa_n else ""
                    ev_g = df_anno[df_anno["Giorno"] == g_idx]
                    corsie = ["", "", ""]
                    for _, row in ev_g.sort_values("Ora_Esatta").iterrows():
                        c_idx = assegna_corsia(row["Ora_Esatta"])
                        corsie[c_idx] += f"<div>{row['Ora_Esatta']}</div>"
                    cls = ["time-slot " + ("busy-slot" if c else "free-slot") for c in corsie]
                    rows_html += f"<tr><td class='day-label'>{g_abr[g_idx]} ({len(ev_g)}) {f_lbl}</td><td class='{cls[0]}'>{corsie[0]}</td><td class='{cls[1]}'>{corsie[1]}</td><td class='{cls[2]}'>{corsie[2]}</td></tr>"
                st.markdown(f"<div class='year-card'><h3 style='text-align:center;'>{anno}</h3><table class='grid-table'>{rows_html}</table></div>", unsafe_allow_html=True)

    # --- RIPRISTINO MAPPA ORARIA FREQUENTE ---
    st.markdown("---")
    st.subheader("📊 Mappa Oraria delle Frequenze")
    st.write("In questa tabella vedi dove si concentra il lavoro indipendentemente dall'anno:")
    ordine_fasce = ["08:00-09:00", "09:00-11:00", "11:00-13:00", "13:00-15:00", "15:00-17:00", "17:00-19:00", "19:00-22:00"]
    pivot_orari = df.pivot_table(index="Giorno", columns="Fascia", values="Anno", aggfunc='count', fill_value=0)
    pivot_orari.index = pivot_orari.index.map(g_abr)
    pivot_orari = pivot_orari.reindex(index=["Lun","Mar","Mer","Gio","Ven","Sab"], columns=ordine_fasce).fillna(0).astype(int)
    st.dataframe(pivot_orari.style.background_gradient(cmap="Blues", axis=None).format("{:.0f}"), use_container_width=True)

    st.subheader("📈 Trend Mensile")
    df["Mese_T"] = df["Data"].apply(lambda x: mesi_it[x.month])
    pivot_mesi = df.pivot_table(index="Mese_T", columns="Anno", values="Ora_Num", aggfunc="count", fill_value=0)
    pivot_mesi = pivot_mesi.reindex([mesi_it[m] for m in range(1,13) if mesi_it[m] in pivot_mesi.index])
    st.dataframe(pivot_mesi.style.background_gradient(cmap="Reds"), use_container_width=True)
else:
    st.warning("⚠️ Nessun dato trovato. Verifica il link di Google Drive.")
