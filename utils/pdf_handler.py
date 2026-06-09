# utils/pdf_handler.py
import os

# On définit où seront stockés les PDF
UPLOAD_FOLDER = 'static/uploads/emplois'

def initialiser_dossiers():
    """ Crée les dossiers de stockage s'ils n'existent pas encore """
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
        print(f"📁 Dossier créé : {UPLOAD_FOLDER}")
    else:
        print("📁 Dossier de stockage déjà prêt.")

def verifier_extension_pdf(filename):
    """ Vérifie si le fichier est bien un PDF """
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'pdf'

if __name__ == "__main__":
    initialiser_dossiers()