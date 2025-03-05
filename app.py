from flask import Flask, render_template_string, request, jsonify
from bakong_khqr import KHQR
import time
import paho.mqtt.client as mqtt

# Step 1: Initialize KHQR with your Bakong Developer Token
bakong_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJkYXRhIjp7ImlkIjoiZDViNzE1MjU3ZmUzNGEyMCJ9LCJpYXQiOjE3NDEwMTk1MzEsImV4cCI6MTc0ODc5NTUzMX0.RebHZpouxe64Cc_u6O3kXRDDjxIQl8KiXnMlTlEGUKw"
khqr = KHQR(bakong_token)

# Merchant Information
merchant_info = {
    "bank_account": "seangly_sou@aclb",  # Your Bakong Account ID
    "merchant_name": "Maker.io Store",
    "merchant_city": "PHNOM PENH",
    "currency": "KHR",  # Use "KHR" directly
    "store_label": "ProfilePal",
    "phone_number": "85510341002",
    "terminal_label": "Cashier-01",
}

# Flask App
app = Flask(__name__)

# Global variables to store QR code details
qr_data = {
    "qr_code": None,
    "amount": None,
    "md5_hash": None,
    "timestamp": None,
    "payment_status": None,  # Track payment status
    "cooldown_end_time": None,  # Cooldown end time after successful payment
}

# MQTT Configuration
mqtt_broker = "test.mosquitto.org"
mqtt_port = 1883
mqtt_topic = "washing/machine2025"

# Function to publish MQTT message
def publish_mqtt_message(message):
    try:
        client = mqtt.Client()
        client.connect(mqtt_broker, mqtt_port, 60)
        client.publish(mqtt_topic, message)
        print(f"Published MQTT message: {message} to topic: {mqtt_topic}")
        client.disconnect()
    except Exception as e:
        print(f"Error publishing MQTT message: {e}")

# Route for the main page
@app.route("/", methods=["GET", "POST"])
def index():
    global qr_data

    if request.method == "POST":
        amount = int(request.form.get("amount"))

        try:
            print(f"Generating Dynamic QR Code for {amount} KHR...")
            qr_code = khqr.create_qr(
                bank_account=merchant_info["bank_account"],
                merchant_name=merchant_info["merchant_name"],
                merchant_city=merchant_info["merchant_city"],
                amount=amount,
                currency=merchant_info["currency"],
                store_label=merchant_info["store_label"],
                phone_number=merchant_info["phone_number"],
                bill_number=f"TRX{amount}",  # Unique bill number
                terminal_label=merchant_info["terminal_label"],
                static=False,  # Dynamic QR Code
            )
            if not qr_code:
                raise ValueError("Empty QR code string")
            print(f"Generated Dynamic QR Code for {amount} KHR: {qr_code}")

            md5_hash = khqr.generate_md5(qr_code)
            print(f"Generated MD5 Hash for {amount} KHR: {md5_hash}")

            qr_data = {
                "qr_code": qr_code,
                "amount": amount,
                "md5_hash": md5_hash,
                "timestamp": time.time(),  # Current timestamp
                "payment_status": "UNPAID",  # Initial payment status
                "cooldown_end_time": None,  # No cooldown initially
            }

        except Exception as e:
            print(f"Error generating QR Code for {amount} KHR: {e}")
            qr_data = {"qr_code": None, "amount": None, "md5_hash": None, "timestamp": None, "payment_status": None, "cooldown_end_time": None}

    # HTML Template with Buttons and QR Code Display
    html_template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>QR Code Generator</title>
        <!-- Bootstrap CSS -->
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            body { padding: 20px; background-color: #f8f9fa; }
            .container { max-width: 600px; margin: auto; text-align: center; }
            button { margin: 5px; }
            img { margin-top: 20px; border: 5px solid #fff; border-radius: 10px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); }
            .message { margin-top: 20px; font-size: 18px; }
            .success { color: green; }
            .error { color: red; }
        </style>
        <script>
            function checkPaymentStatus() {
                fetch('/check-payment', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({}),
                })
                .then(response => response.json())
                .then(data => {
                    const qrCodeContainer = document.getElementById('qr-code-container');
                    const messageElement = document.getElementById('message');

                    if (data.status === 'PAID') {
                        messageElement.innerText = 'Thank You!';
                        qrCodeContainer.style.display = 'none';
                        startCooldown(data.cooldown_time);
                    } else if (data.status === 'EXPIRED') {
                        messageElement.innerText = 'QR Code Expired. Please select an option to start QR.';
                        qrCodeContainer.style.display = 'none';
                        location.reload(); // Auto-refresh the browser
                    } else if (data.status === 'UNPAID') {
                        messageElement.innerText = 'Status: Checking...';
                    }
                })
                .catch(error => console.error('Error checking payment status:', error));
            }

            function startCooldown(cooldown_time) {
                let remainingTime = cooldown_time;
                const cooldownMessage = document.getElementById('cooldown-message');
                cooldownMessage.style.display = 'block';

                const interval = setInterval(() => {
                    remainingTime -= 1;
                    cooldownMessage.innerText = `Please wait ${remainingTime} seconds before generating a new QR Code.`;

                    if (remainingTime <= 0) {
                        clearInterval(interval);
                        cooldownMessage.style.display = 'none';
                        location.reload(); // Auto-refresh the browser
                    }
                }, 1000);
            }

            // Poll payment status every 2 seconds
            setInterval(checkPaymentStatus, 2000);
        </script>
    </head>
    <body>
        <div class="container">
            <h1>Select Amount</h1>
            <form method="POST">
                <button type="submit" name="amount" value="100" class="btn btn-primary">100៛</button>
                <button type="submit" name="amount" value="200" class="btn btn-success">200៛</button>
                <button type="submit" name="amount" value="300" class="btn btn-warning">300៛</button>
            </form>

            <div id="qr-code-container" class="mt-4">
                {% if qr_data['qr_code'] %}
                    <h2>QR Code for {{ qr_data['amount'] }}៛</h2>
                    <img src="https://api.qrserver.com/v1/create-qr-code/?data={{ qr_data['qr_code'] }}&size=250x250" alt="QR Code">
                    <p id="message">Status: Checking...</p>
                {% else %}
                    <p class="message">Please select an option to start QR.</p>
                {% endif %}
            </div>

            <div id="cooldown-message" class="message" style="display: none;"></div>
        </div>

        <!-- Bootstrap JS -->
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/js/bootstrap.bundle.min.js"></script>
    </body>
    </html>
    """

    return render_template_string(html_template, qr_data=qr_data)

# Route to check payment status
@app.route("/check-payment", methods=["POST"])
def check_payment_status():
    global qr_data

    if not qr_data["qr_code"]:
        return jsonify({"status": "ERROR", "message": "No QR code generated."})

    current_time = time.time()
    if current_time - qr_data["timestamp"] > 120:
        qr_data["payment_status"] = "EXPIRED"
        return jsonify({"status": "EXPIRED", "message": "QR code has expired."})

    max_retries = 5
    retry_delay = 2
    for attempt in range(max_retries):
        try:
            payment_status = khqr.check_payment(qr_data["md5_hash"])
            print(f"Attempt {attempt + 1}: Payment status for {qr_data['amount']} KHR: {payment_status}")
            if payment_status == "PAID":
                qr_data["payment_status"] = "PAID"
                cooldown_time = {100: 180, 200: 240, 300: 300}.get(qr_data["amount"], 0)
                qr_data["cooldown_end_time"] = time.time() + cooldown_time
                publish_mqtt_message("Payment Successful: Machine Start")
                return jsonify({"status": "PAID", "cooldown_time": cooldown_time})
            elif payment_status == "UNPAID":
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                else:
                    return jsonify({"status": "UNPAID"})
            else:
                return jsonify({"status": "ERROR", "message": "Unexpected payment status."})
        except Exception as e:
            print(f"Error checking payment status: {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                return jsonify({"status": "ERROR", "message": str(e)})

# Route to expire QR code
@app.route("/expire-qr", methods=["POST"])
def expire_qr():
    global qr_data
    qr_data["payment_status"] = "EXPIRED"
    return jsonify({"status": "SUCCESS"})

if __name__ == "__main__":
    print("Starting local server at http://127.0.0.1:5000")
    app.run(debug=True)