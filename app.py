from flask import Flask, request, jsonify
from deepface import DeepFace
import numpy as np

app = Flask(__name__)

def convert(obj):
    """Convertit récursivement les types NumPy en types Python natifs"""
    if isinstance(obj, dict):
        return {k: convert(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert(i) for i in obj]
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    return obj

@app.route("/verify", methods=["POST"])
def verify():
    try:
        img1 = request.files["img1"]
        img2 = request.files["img2"]

        img1.save("img1.jpg")
        img2.save("img2.jpg")

        result = DeepFace.verify("img1.jpg", "img2.jpg", enforce_detection=False)
        result = convert(result)  # ✅ conversion avant jsonify
        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == "__main__":
    app.run(debug=True)