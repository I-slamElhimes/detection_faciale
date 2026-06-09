# test_identifier.py
import requests
import json

url = "http://127.0.0.1:5000/identifier"

try:
    files = {
        "image": open("data/photos/islam2.jpg", "rb")
    }

    response = requests.post(url, files=files)
    data = response.json()

    print("\n📦 Résultat :")
    print(json.dumps(data, indent=2, ensure_ascii=False))

    if data.get("identifie"):
        print(f"\n✅ Personne reconnue : {data['nom']} {data['prenom']}")
        print(f"📊 Distance : {data['distance']:.4f}")
    else:
        print(f"\n❌ Personne non reconnue")
        print(f"📊 Distance : {data['distance']:.4f}")

except Exception as e:
    print("Erreur :", str(e))