# emploi_manager.py
# ─────────────────────────────────────────────────────────────────────────────
# Gestion de l'emploi du temps :
#   - Stocker le PDF en base64 dans MongoDB (jamais sur disque)
#   - Récupérer le PDF d'un groupe
#   - Supprimer l'emploi du temps d'un groupe
# ─────────────────────────────────────────────────────────────────────────────

import base64
from db_config import get_db
from bson.objectid import ObjectId
from datetime import datetime


def assigner_pdf_au_groupe(groupe_id, chemin_pdf):
    """
    Lit un fichier PDF depuis le disque, le convertit en base64
    et le stocke dans MongoDB (collection groupes).
    Le fichier disque n'est PAS supprimé — c'est à l'appelant de le faire.

    Args:
        groupe_id  : str ou ObjectId
        chemin_pdf : chemin local vers le fichier PDF (ex: "uploads/planning.pdf")
    """
    db = get_db()

    with open(chemin_pdf, "rb") as f:
        contenu_b64 = base64.b64encode(f.read()).decode("utf-8")

    nom_fichier = chemin_pdf.split("/")[-1].split("\\")[-1]

    result = db["groupes"].update_one(
        {"_id": ObjectId(groupe_id) if isinstance(groupe_id, str) else groupe_id},
        {"$set": {
            "emploi_du_temps":    contenu_b64,          # ✅ base64 dans MongoDB
            "emploi_nom_fichier": nom_fichier,
            "emploi_uploade_le":  datetime.now()
        }}
    )

    if result.modified_count > 0:
        print(f"✅ Emploi du temps '{nom_fichier}' stocké en base64 pour le groupe {groupe_id}")
    else:
        print("⚠️  Aucune modification — vérifiez l'ID du groupe.")


def get_pdf_groupe(groupe_id):
    """
    Retourne le contenu base64 du PDF d'emploi du temps d'un groupe.

    Returns:
        dict { "nom_fichier": str, "pdf_base64": str, "uploade_le": datetime }
        ou None si pas d'emploi du temps.
    """
    db     = get_db()
    groupe = db["groupes"].find_one(
        {"_id": ObjectId(groupe_id) if isinstance(groupe_id, str) else groupe_id}
    )

    if not groupe:
        print(f"❌ Groupe {groupe_id} introuvable.")
        return None

    if not groupe.get("emploi_du_temps"):
        print(f"⚠️  Aucun emploi du temps pour le groupe '{groupe.get('nom')}'.")
        return None

    return {
        "nom_fichier": groupe.get("emploi_nom_fichier", "emploi.pdf"),
        "pdf_base64":  groupe["emploi_du_temps"],
        "uploade_le":  groupe.get("emploi_uploade_le")
    }


def supprimer_emploi_groupe(groupe_id):
    """Supprime l'emploi du temps d'un groupe."""
    db = get_db()
    db["groupes"].update_one(
        {"_id": ObjectId(groupe_id) if isinstance(groupe_id, str) else groupe_id},
        {"$unset": {
            "emploi_du_temps":    "",
            "emploi_nom_fichier": "",
            "emploi_uploade_le":  ""
        }}
    )
    print(f"✅ Emploi du temps supprimé pour le groupe {groupe_id}")


# ── TEST ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    db = get_db()
    un_groupe = db["groupes"].find_one()

    if not un_groupe:
        print("❌ Lance seed_data.py d'abord !")
    else:
        print(f"Groupe trouvé : {un_groupe['nom']} (ID: {un_groupe['_id']})")

        # Créer un PDF fictif pour le test
        import os
        pdf_test = "temp_test.pdf"
        with open(pdf_test, "wb") as f:
            f.write(b"%PDF-1.4 test")

        assigner_pdf_au_groupe(str(un_groupe["_id"]), pdf_test)

        result = get_pdf_groupe(str(un_groupe["_id"]))
        if result:
            print(f"✅ PDF récupéré : {result['nom_fichier']} ({len(result['pdf_base64'])} chars base64)")

        os.remove(pdf_test)