# app/routes/payment_frontend.py
from flask import Blueprint, request, jsonify
from app.services.payment_service import PaymentService
from app.extensions import cors

payment_bp = Blueprint("payment_frontend", __name__)
cors.init_app(payment_bp, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

@payment_bp.route("/stk_push", methods=["POST"])
def stk_push():
    data = request.json or {}
    amount = data.get("amount")
    phone_number = data.get("phone_number")
    account_reference = data.get("account_reference", "DONATION")
    transaction_desc = data.get("transaction_desc", "Charity Donation")

    if not amount or not phone_number:
        return jsonify({"success": False, "error": "Missing amount or phone_number"}), 400

    try:
        result = PaymentService.initiate_stk_push(
            amount=amount,
            phone_number=phone_number,
            account_reference=account_reference,
            transaction_desc=transaction_desc
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
