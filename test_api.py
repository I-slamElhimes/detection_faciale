import requests
import json

url = "http://127.0.0.1:5000/verify"

files = {
    "img1": open("img1.jpg", "rb"),
    "img2": open("img2.jpg", "rb")
}

response = requests.post(url, files=files)

print("Status:", response.status_code)

# ✅ Affichage JSON propre et lisible
data = response.json()
print("Résultat:")
print(json.dumps(data, indent=2, ensure_ascii=False))

# ✅ Résumé clair
if "verified" in data:
    if data["verified"]:
        print("\n✅ Les deux visages appartiennent à la MÊME personne")
    else:
        print("\n❌ Les deux visages sont des personnes DIFFÉRENTES")
    print(f"📊 Distance : {data.get('distance', 'N/A'):.4f}")
    print(f"📏 Seuil    : {data.get('threshold', 'N/A'):.4f}")
else:
    print("\n⚠️ Erreur:", data.get("error"))