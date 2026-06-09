# utils/embedding.py
from deepface import DeepFace
import base64
import tempfile
import os


def extraire_embedding(image_path):
    """
    Extrait le vecteur ArcFace 512D depuis un fichier image.
    Retourne une liste de 512 floats.
    """
    result = DeepFace.represent(
        img_path=image_path,
        model_name="ArcFace",
        enforce_detection=False
    )
    return result[0]["embedding"]


def extraire_embedding_depuis_base64(image_base64):
    """
    Extrait le vecteur ArcFace 512D depuis une image en base64.
    Utilisé dans /identifier quand la caméra envoie un frame.
    """
    img_data = base64.b64decode(image_base64)
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        tmp.write(img_data)
        tmp_path = tmp.name
    try:
        embedding = extraire_embedding(tmp_path)
    finally:
        os.remove(tmp_path)
    return embedding