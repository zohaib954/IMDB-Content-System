from flask import jsonify


def success_response(data=None, message="Success", status_code=200, meta=None):
    payload = {"success": True, "message": message}
    if data is not None:
        payload["data"] = data
    if meta is not None:
        payload["meta"] = meta
    return jsonify(payload), status_code


def error_response(message="An error occurred", status_code=400, errors=None):
    payload = {"success": False, "message": message}
    if errors:
        payload["errors"] = errors
    return jsonify(payload), status_code