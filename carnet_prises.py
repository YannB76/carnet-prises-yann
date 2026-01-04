import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime, time
from io import BytesIO  # pour l'export Excel

# Fichier CSV et dossier photos
DATA_FILE = Path("carnet_prises.csv")
PHOTOS_DIR = Path("photos")
PHOTOS_DIR.mkdir(exist_ok=True)

# Colonnes du carnet
COLUMNS = [
    "date",
    "heure",
    "espece",
    "taille_cm",
    "poids",
    "unite_poids",
    "spot",
    "type_leurre",
    "nom_leurre",
    "conditions",
    "remis_a_leau",
    "commentaire",
    "photo_fichier",
]


def parse_date_str(value):
    """Essaie plusieurs formats de date et renvoie une date Python."""
    if pd.isna(value):
        return datetime.today().date()
    s = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return datetime.today().date()


def parse_time_str(value):
    """Essaie plusieurs formats d'heure pour les données déjà enregistrées."""
    if pd.isna(value) or value == "":
        now = datetime.now()
        return time(hour=now.hour, minute=now.minute)
    s = str(value).strip()
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            return datetime.strptime(s, fmt).time()
        except ValueError:
            continue
    now = datetime.now()
    return time(hour=now.hour, minute=now.minute)


def parse_time_from_text(field_value: str) -> time:
    """
    Parse une heure au format HH:MM à partir du champ texte.
    Lève une erreur si la valeur n'est pas valide.
    """
    s = field_value.strip()

    # Normalise : 7:5 -> 07:05
    if ":" in s:
        parts = s.split(":")
        if len(parts) == 2:
            h, m = parts[0].zfill(2), parts[1].zfill(2)
            s = f"{h}:{m}"

    return datetime.strptime(s, "%H:%M").time()


def safe_float(value, default=0.0):
    try:
        if pd.isna(value) or value == "":
            return default
        return float(value)
    except Exception:
        return default


@st.cache_data
def load_data() -> pd.DataFrame:
    if DATA_FILE.exists():
        df = pd.read_csv(DATA_FILE, sep=";", encoding="utf-8")
    else:
        df = pd.DataFrame(columns=COLUMNS)

    # S'assurer que toutes les colonnes existent
    for col in COLUMNS:
        if col not in df.columns:
            df[col] = ""

    return df[COLUMNS]


def save_data(df: pd.DataFrame):
    try:
        df.to_csv(DATA_FILE, sep=";", index=False, encoding="utf-8")
    except PermissionError:
        st.error(
            "Impossible d'écrire dans le fichier 'carnet_prises.csv'.\n"
            "Vérifie qu'il n'est pas ouvert dans Excel ou un autre programme, puis réessaie."
        )


def enregistrer_photo(file) -> str:
    """Enregistre la photo uploadée dans /photos et renvoie le chemin."""
    if file is None:
        return ""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = file.name.replace(" ", "_")
    filename = f"{timestamp}_{safe_name}"
    filepath = PHOTOS_DIR / filename
    with open(filepath, "wb") as f:
        f.write(file.read())
    return str(filepath)


def to_excel_bytes(df: pd.DataFrame) -> bytes:
    """Convertit le DataFrame complet en fichier Excel en mémoire."""
    output = BytesIO()
    # on retire l'index et on garde toutes les colonnes
    df.to_excel(output, index=False, sheet_name="Prises")
    output.seek(0)
    return output.read()


def main():
    st.set_page_config(
        page_title="Carnet de prises Yann 🎣",
        layout="wide",
    )

    st.title("📘 Carnet de prises – Yann")
    st.write("Enregistre, édite tes prises et associe une photo.")

    df = load_data()

    # ---------- AJOUT D'UNE PRISE ----------
    st.sidebar.header("➕ Ajouter une prise")

    now = datetime.now()
    date_prise = st.sidebar.date_input("Date", value=now.date())

    heure_default_str = now.strftime("%H:%M")
    heure_str = st.sidebar.text_input("Heure (HH:MM)", value=heure_default_str)

    espece = st.sidebar.text_input("Espèce", value="Bar")
    taille = st.sidebar.number_input("Taille (cm)", min_value=0.0, step=0.5)
    poids = st.sidebar.number_input("Poids", min_value=0.0, step=0.05)
    unite_poids = st.sidebar.selectbox("Unité du poids", ["kg", "g"], index=0)

    spot = st.sidebar.text_input("Spot", value="Le Havre")
    type_leurre = st.sidebar.selectbox(
        "Type de leurre",
        ["Stickbait", "Jig", "Leurre souple", "Créature", "Autre"],
        index=0,
    )
    nom_leurre = st.sidebar.text_input("Nom du leurre", value="")

    conditions = st.sidebar.text_area(
        "Conditions (marée, météo, vent...)",
        value="",
        height=80,
    )

    remis_a_leau = st.sidebar.radio("Remis à l'eau ?", ["Oui", "Non"], index=0)
    commentaire = st.sidebar.text_area("Commentaire", value="", height=80)

    photo_new = st.sidebar.file_uploader(
        "Photo de la prise (optionnel)", type=["jpg", "jpeg", "png"]
    )

    if st.sidebar.button("✅ Enregistrer la prise"):
        try:
            heure_prise = parse_time_from_text(heure_str)
        except Exception:
            st.sidebar.error("Heure invalide. Utilise le format HH:MM (ex : 06:30).")
        else:
            photo_path = enregistrer_photo(photo_new)

            new_row = {
                "date": date_prise.strftime("%Y-%m-%d"),
                "heure": heure_prise.strftime("%H:%M"),
                "espece": espece,
                "taille_cm": taille,
                "poids": poids,
                "unite_poids": unite_poids,
                "spot": spot,
                "type_leurre": type_leurre,
                "nom_leurre": nom_leurre,
                "conditions": conditions,
                "remis_a_leau": remis_a_leau,
                "commentaire": commentaire,
                "photo_fichier": photo_path,
            }

            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            save_data(df)
            st.sidebar.success("🎣 Prise enregistrée !")
            st.cache_data.clear()
            df = load_data()

    # ---------- LISTE DES PRISES ----------
    st.subheader("📊 Mes prises enregistrées")

    if df.empty:
        st.info("Aucune prise enregistrée pour le moment.")
        return

    # Filtres
    with st.expander("🔍 Filtres"):
        col1, col2, col3 = st.columns(3)
        with col1:
            espece_filter = st.multiselect("Espèce", sorted(df["espece"].dropna().unique()))
        with col2:
            spot_filter = st.multiselect("Spot", sorted(df["spot"].dropna().unique()))
        with col3:
            leurre_filter = st.multiselect(
                "Nom du leurre", sorted(df["nom_leurre"].dropna().unique())
            )

        filtered_df = df.copy()
        if espece_filter:
            filtered_df = filtered_df[filtered_df["espece"].isin(espece_filter)]
        if spot_filter:
            filtered_df = filtered_df[filtered_df["spot"].isin(spot_filter)]
        if leurre_filter:
            filtered_df = filtered_df[filtered_df["nom_leurre"].isin(leurre_filter)]

    # Affichage du tableau avec numérotation à partir de 1
    df_display = filtered_df.drop(columns=["photo_fichier"]).copy()
    df_display.index = df_display.index + 1
    df_display.index.name = "prise_n°"
    st.dataframe(df_display, use_container_width=True)

    # ---------- EXPORT EXCEL ----------
    st.markdown("### 📤 Export des données")
    excel_bytes = to_excel_bytes(df)
    st.download_button(
        label="📥 Télécharger toutes les prises en Excel (.xlsx)",
        data=excel_bytes,
        file_name="carnet_prises_yann.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    st.markdown("---")

    # ---------- STATS AVANCÉES ----------
    st.markdown("### 📈 Stats par spot et par leurre")

    col_stats1, col_stats2 = st.columns(2)

    with col_stats1:
        st.markdown("#### Par spot")
        if not df.empty:
            stats_spot = (
                df.groupby("spot")
                .agg(
                    nb_prises=("espece", "count"),
                    taille_moy_cm=("taille_cm", "mean"),
                )
                .sort_values("nb_prises", ascending=False)
                .round(1)
            )
            st.dataframe(stats_spot)
        else:
            st.info("Pas encore de prises pour calculer les stats par spot.")

    with col_stats2:
        st.markdown("#### Par type de leurre")
        if not df.empty:
            stats_leurre = (
                df.groupby("type_leurre")
                .agg(
                    nb_prises=("espece", "count"),
                    taille_moy_cm=("taille_cm", "mean"),
                )
                .sort_values("nb_prises", ascending=False)
                .round(1)
            )
            st.dataframe(stats_leurre)
        else:
            st.info("Pas encore de prises pour calculer les stats par leurre.")

    st.markdown("---")

    # ---------- GALERIE PHOTOS ----------
    st.markdown("### 📸 Galerie photos")

    photos_df = filtered_df[filtered_df["photo_fichier"].astype(str) != ""]
    if photos_df.empty:
        st.info("Aucune photo enregistrée pour les prises filtrées.")
    else:
        # On les trie par date/heure décroissante
        photos_df = photos_df.sort_values(["date", "heure"], ascending=False)

        # Affichage en grille (3 par ligne)
        cols = st.columns(3)
        idx_col = 0

        for _, row in photos_df.iterrows():
            with cols[idx_col]:
                try:
                    st.image(row["photo_fichier"], use_container_width=True)
                    st.caption(
                        f'{row["date"]} {row["heure"]} – {row["espece"]} '
                        f'{row["taille_cm"]} cm, {row["spot"]}'
                    )
                except Exception:
                    st.warning("Impossible d'afficher une photo (chemin invalide ?)")

            idx_col = (idx_col + 1) % 3
            if idx_col == 0:
                cols = st.columns(3)

    st.markdown("---")

    # ---------- ÉDITION / SUPPRESSION D'UNE PRISE ----------
    st.subheader("✏️ Éditer ou supprimer une prise")

    df_with_idx = df.reset_index().rename(columns={"index": "id_interne"})
    options = [
        (
            row["id_interne"],
            f'{row["id_interne"]} | {row["date"]} {row["heure"]} '
            f'- {row["espece"]} {row["taille_cm"]} cm à {row["spot"]}'
        )
        for _, row in df_with_idx.iterrows()
    ]

    if options:
        option_labels = [label for _, label in options]
        selected_label = st.selectbox(
            "Choisis une prise à éditer / supprimer",
            options=option_labels,
            index=0,
        )

        selected_id = None
        for _id, label in options:
            if label == selected_label:
                selected_id = _id
                break

        if selected_id is not None:
            row = df_with_idx[df_with_idx["id_interne"] == selected_id].iloc[0]

            # ------- FORMULAIRE D'ÉDITION -------
            with st.form("form_edit_prise"):
                st.write("Modifier les informations de la prise :")

                date_edit = st.date_input(
                    "Date",
                    value=parse_date_str(row["date"]),
                )

                # heure en texte ici aussi
                heure_default = parse_time_str(row["heure"]).strftime("%H:%M")
                heure_edit_str = st.text_input("Heure (HH:MM)", value=heure_default)

                espece_edit = st.text_input("Espèce", value=row["espece"])
                taille_edit = st.number_input(
                    "Taille (cm)",
                    min_value=0.0,
                    step=0.5,
                    value=safe_float(row["taille_cm"]),
                )
                poids_edit = st.number_input(
                    "Poids",
                    min_value=0.0,
                    step=0.05,
                    value=safe_float(row["poids"]),
                )
                unite_poids_edit = st.selectbox(
                    "Unité du poids",
                    ["kg", "g"],
                    index=0 if str(row["unite_poids"]) == "kg" else 1,
                )

                spot_edit = st.text_input("Spot", value=row["spot"])
                type_leurre_edit = st.selectbox(
                    "Type de leurre",
                    ["Stickbait", "Jig", "Leurre souple", "Créature", "Autre"],
                    index=(
                        ["Stickbait", "Jig", "Leurre souple", "Créature", "Autre"]
                        .index(str(row["type_leurre"]))
                        if str(row["type_leurre"]) in ["Stickbait", "Jig", "Leurre souple", "Créature", "Autre"]
                        else 0
                    ),
                )
                nom_leurre_edit = st.text_input("Nom du leurre", value=row["nom_leurre"])

                conditions_edit = st.text_area(
                    "Conditions (marée, météo, vent...)",
                    value=row["conditions"],
                    height=80,
                )

                remis_edit = st.radio(
                    "Remis à l'eau ?",
                    ["Oui", "Non"],
                    index=0 if str(row["remis_a_leau"]) == "Oui" else 1,
                )

                commentaire_edit = st.text_area(
                    "Commentaire", value=row["commentaire"], height=80
                )

                st.write("Photo actuelle :")
                if isinstance(row["photo_fichier"], str) and row["photo_fichier"]:
                    try:
                        st.image(
                            row["photo_fichier"],
                            caption="Photo de la prise",
                            use_container_width=True,
                        )
                    except Exception:
                        st.warning("Impossible d'afficher la photo (chemin invalide ?)")
                else:
                    st.info("Aucune photo associée.")

                photo_edit = st.file_uploader(
                    "Remplacer / ajouter une photo",
                    type=["jpg", "jpeg", "png"],
                )

                submitted = st.form_submit_button("💾 Enregistrer les modifications")

                if submitted:
                    try:
                        heure_edit = parse_time_from_text(heure_edit_str)
                    except Exception:
                        st.error("Heure invalide. Utilise le format HH:MM (ex : 06:30).")
                    else:
                        photo_path_edit = row["photo_fichier"]
                        if photo_edit is not None:
                            photo_path_edit = enregistrer_photo(photo_edit)

                        df.loc[selected_id, "date"] = date_edit.strftime("%Y-%m-%d")
                        df.loc[selected_id, "heure"] = heure_edit.strftime("%H:%M")
                        df.loc[selected_id, "espece"] = espece_edit
                        df.loc[selected_id, "taille_cm"] = taille_edit
                        df.loc[selected_id, "poids"] = poids_edit
                        df.loc[selected_id, "unite_poids"] = unite_poids_edit
                        df.loc[selected_id, "spot"] = spot_edit
                        df.loc[selected_id, "type_leurre"] = type_leurre_edit
                        df.loc[selected_id, "nom_leurre"] = nom_leurre_edit
                        df.loc[selected_id, "conditions"] = conditions_edit
                        df.loc[selected_id, "remis_a_leau"] = remis_edit
                        df.loc[selected_id, "commentaire"] = commentaire_edit
                        df.loc[selected_id, "photo_fichier"] = photo_path_edit

                        save_data(df)
                        st.success("✅ Prise mise à jour avec succès.")
                        st.cache_data.clear()
                        df = load_data()

            # ------- BOUTON SUPPRESSION -------
            if st.button("🗑️ Supprimer cette prise"):
                df = df.drop(index=selected_id).reset_index(drop=True)
                save_data(df)
                st.success("🗑️ Prise supprimée.")
                st.cache_data.clear()
                st.rerun()

        else:
            st.info("Sélection invalide.")
    else:
        st.info("Aucune prise sélectionnable pour l'édition / suppression.")


if __name__ == "__main__":
    main()
