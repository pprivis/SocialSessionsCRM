from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Allows cross-origin requests from Wix

@app.route('/')
def home():
    return "✅ Flask backend is running!"

@app.route('/api/pop_order', methods=['POST'])
def receive_order():
    try:
        data = request.get_json()
        print("✅ Received order data:", data)

        # You could add more logic here (e.g., save to database)

        return jsonify({"success": True, "message": "Order received"})
    except Exception as e:
        print("❌ Error receiving order:", str(e))
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
