from flask import Flask, request, jsonify
import requests

PROXY_APP = Flask(__name__)
SERVICES = {"user": "http://user_service:5001"}

@PROXY_APP.route('/<service>/<path:path>', methods=['POST', 'GET', 'PUT', 'DELETE', 'PATCH'])
def proxy(service, path):
    if service not in SERVICES:
        return jsonify({"error": "Service not found"}), 404

    url = f'{SERVICES[service]}/{path}'
    headers = {key: value for key, value in request.headers if key.lower() != 'host'}
    response = requests.request(
        method=request.method,
        url=url,
        headers=headers,
        data=request.get_data(),
        params=request.args,
        cookies=request.cookies
    )

    return (response.content, response.status_code, response.headers.items())

if __name__ == "__main__":
    PROXY_APP.run(debug=True, host="0.0.0.0", port=5000)
