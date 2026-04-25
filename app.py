from flask import Flask, request, jsonify
from deepface import DeepFace

app = Flask(__name__)

@app.route("/")
def home():
    return "API works"

@app.route("/verify", methods=["POST"])
def verify():
    img1 = request.files["img1"]
    img2 = request.files["img2"]

    img1.save("img1.jpg")
    img2.save("img2.jpg")

    result = DeepFace.verify("img1.jpg", "img2.jpg")

    return jsonify(result)

if __name__ == "__main__":
    app.run(debug=True)