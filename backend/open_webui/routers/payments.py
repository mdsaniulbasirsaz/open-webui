import os
import logging
import uuid
from typing import Optional
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from requests import HTTPError, RequestException
from requests.exceptions import ConnectionError, Timeout
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from open_webui.internal.db import get_session
from open_webui.models.payments import (
    PaymentEvents,
    PaymentTransactions,
    PaymentTransactionModel,
)
from open_webui.utils.auth import get_current_user
from open_webui.utils.bkash_client import BkashClient

log = logging.getLogger(__name__)

router = APIRouter()


class CreateBkashPaymentForm(BaseModel):
    plan_id: Optional[str] = None
    amount: float
    currency: str = "BDT"
    payer_reference: Optional[str] = None
    merchant_invoice_number: Optional[str] = None
    intent: str = "sale"
    mode: str = "0011"


class ExecuteBkashPaymentForm(BaseModel):
    payment_id: str


class QueryBkashPaymentForm(BaseModel):
    payment_id: str


class BkashPaymentResponse(BaseModel):
    status: str
    payment_id: Optional[str] = None
    bkash_url: Optional[str] = None
    trx_id: Optional[str] = None
    message: Optional[str] = None
    model_config = ConfigDict(extra="allow")


class BkashCallbackPayload(BaseModel):
    paymentID: Optional[str] = None
    payment_id: Optional[str] = None
    status: Optional[str] = None
    statusCode: Optional[str] = None
    statusMessage: Optional[str] = None
    model_config = ConfigDict(extra="allow")


def _build_bkash_client(request: Request) -> BkashClient:
    config = request.app.state.config
    base_url = config.BKASH_BASE_URL
    app_key = config.BKASH_APP_KEY or config.BKASH_CHECKOUT_URL_APP_KEY
    app_secret = config.BKASH_APP_SECRET or config.BKASH_CHECKOUT_URL_APP_SECRET
    username = config.BKASH_USERNAME or config.BKASH_CHECKOUT_URL_USER_NAME
    password = config.BKASH_PASSWORD or config.BKASH_CHECKOUT_URL_PASSWORD

    required = [base_url, app_key, app_secret, username, password]
    if not all(required):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="bKash configuration is incomplete.",
        )

    return BkashClient(
        base_url=base_url,
        app_key=app_key,
        app_secret=app_secret,
        username=username,
        password=password,
        timeout_seconds=config.BKASH_TIMEOUT_SECONDS,
    )


def _normalize_status(payload: dict) -> str:
    status_code = payload.get("statusCode") or payload.get("status")
    transaction_status = payload.get("transactionStatus")
    status_value = None
    if transaction_status:
        status_value = str(transaction_status).strip().lower()
    elif status_code is not None:
        status_value = str(status_code).strip().lower()

    if status_value:
        if "cancel" in status_value or status_value in {"aborted", "abort"}:
            return "canceled"
        if any(token in status_value for token in ("fail", "error", "reject", "declin")):
            return "failed"

    if status_code == "0000":
        return "executed"
    return status_value or "unknown"


def _extract_bkash_payload(exc: HTTPError) -> dict:
    response = exc.response
    if response is None:
        return {}
    try:
        payload = response.json()
    except ValueError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _extract_bkash_message(payload: dict) -> Optional[str]:
    return (
        payload.get("statusMessage")
        or payload.get("message")
        or payload.get("errorMessage")
        or payload.get("error")
    )


def _should_redirect_callback(request: Request) -> bool:
    accept = request.headers.get("accept", "").lower()
    redirect_flag = request.query_params.get("redirect") in {
        "1",
        "true",
    }

    if request.method == "GET":
        if "text/html" in accept or accept in {"", "*/*"}:
            return True
        if redirect_flag:
            return True
        return any(
            request.query_params.get(key)
            for key in ("paymentID", "payment_id", "status", "statusMessage", "statusCode")
        )

    if request.method == "POST":
        # Avoid redirecting server-to-server webhooks unless the caller explicitly looks like a browser.
        if redirect_flag or ("text/html" in accept):
            return True
        # bKash may POST back to the callback URL with query parameters (e.g. signature/paymentID).
        if request.query_params.get("signature"):
            return True
        return any(
            request.query_params.get(key)
            for key in ("paymentID", "payment_id", "status", "statusMessage", "statusCode")
        )

    return False


def _build_callback_redirect_url(
    request: Request, payment_id: str, status_value: Optional[str]
) -> str:
    env_webui_url = os.environ.get("WEBUI_URL", "").strip()
    config_webui_url = str(
        getattr(request.app.state.config, "WEBUI_URL", "") or ""
    ).strip()
    base_url = (env_webui_url or config_webui_url or str(request.base_url)).rstrip("/")
    normalized_status = status_value
    success_statuses = {"executed", "confirmed", "success", "completed"}
    if normalized_status == "canceled":
        path = "/cancel"
    elif normalized_status == "failed":
        path = "/failed"
    elif normalized_status in success_statuses:
        path = "/success"
    else:
        path = "/pricing"
    redirect_params = {"paymentID": payment_id}
    if normalized_status:
        redirect_params["status"] = normalized_status
    return f"{base_url}{path}?{urlencode(redirect_params)}"


def _format_bkash_http_error(exc: HTTPError) -> tuple[str, int]:
    response = exc.response
    if response is None:
        return "bKash request failed. Please try again.", status.HTTP_502_BAD_GATEWAY

    status_code = response.status_code or status.HTTP_502_BAD_GATEWAY
    payload = None
    try:
        payload = response.json()
    except ValueError:
        payload = None

    message = None
    status_detail = None
    if isinstance(payload, dict):
        message = (
            payload.get("statusMessage")
            or payload.get("message")
            or payload.get("errorMessage")
            or payload.get("error")
        )
        status_detail = payload.get("statusCode") or payload.get("code")

    if not message:
        try:
            text = response.text.strip()
        except Exception:
            text = ""
        if text:
            message = text[:200]

    if not message:
        if response.status_code in {401, 403}:
            message = "bKash authentication failed. Verify credentials."
        elif response.status_code == 404:
            message = "bKash endpoint not found. Verify BKASH_BASE_URL."
        else:
            message = f"bKash request failed with status {status_code}."

    if status_detail and isinstance(message, str) and str(status_detail) not in message:
        message = f"{message} (bKash code {status_detail})"

    if status_code < 400 or status_code >= 600:
        status_code = status.HTTP_502_BAD_GATEWAY

    return message, status_code


def _format_bkash_request_error(exc: RequestException) -> str:
    if isinstance(exc, Timeout):
        return "bKash timed out. Please try again."
    if isinstance(exc, ConnectionError):
        return "bKash connection error. Check BKASH_BASE_URL and network access."
    return "bKash request failed. Please try again."


@router.post("/bkash/create", response_model=BkashPaymentResponse)
async def create_bkash_payment(
    request: Request,
    response: Response,
    form_data: CreateBkashPaymentForm,
    user=Depends(get_current_user),
    db: Session = Depends(get_session),
):
    request_id = str(uuid.uuid4())
    response.headers["X-Request-ID"] = request_id
    client = _build_bkash_client(request)

    merchant_invoice_number = form_data.merchant_invoice_number or f"INV{uuid.uuid4().hex[:12]}"
    payer_reference = (
        form_data.payer_reference or request.app.state.config.BKASH_PAYER_REFERENCE
    )
    if not payer_reference:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="payer_reference is required for bKash checkout.",
        )
    payload = {
        "amount": str(form_data.amount),
        "currency": form_data.currency,
        "intent": form_data.intent,
        "merchantInvoiceNumber": merchant_invoice_number,
        "mode": form_data.mode,
    }
    if payer_reference:
        payload["payerReference"] = payer_reference
    if request.app.state.config.BKASH_CALLBACK_URL:
        payload["callbackURL"] = request.app.state.config.BKASH_CALLBACK_URL

    try:
        response_data = client.create_payment(payload)
    except HTTPError as exc:
        message, status_code = _format_bkash_http_error(exc)
        log.exception(
            "bKash create request failed request_id=%s detail=%s",
            request_id,
            message,
        )
        raise HTTPException(status_code=status_code, detail=message) from exc
    except RequestException as exc:
        message = _format_bkash_request_error(exc)
        log.exception("bKash create request failed request_id=%s", request_id)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=message,
        ) from exc
    except Exception as exc:
        log.exception("bKash create request failed request_id=%s", request_id)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="bKash request failed. Please try again.",
        ) from exc
    payment_id = response_data.get("paymentID")
    bkash_url = response_data.get("bkashURL")

    PaymentTransactions.create_transaction(
        user_id=user.id,
        plan_id=form_data.plan_id,
        amount=form_data.amount,
        currency=form_data.currency,
        status=_normalize_status(response_data),
        payment_id=payment_id,
        merchant_invoice_number=merchant_invoice_number,
        raw_response=response_data,
        db=db,
    )

    if not payment_id or not bkash_url:
        log.warning(
            "bKash create failed request_id=%s user_id=%s",
            request_id,
            user.id,
        )
        failure_message = response_data.get("statusMessage") or response_data.get(
            "message"
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=failure_message or "Failed to create bKash payment.",
        )

    log.info(
        "bKash create request_id=%s user_id=%s payment_id=%s",
        request_id,
        user.id,
        payment_id,
    )
    return BkashPaymentResponse(
        status="created",
        payment_id=payment_id,
        bkash_url=bkash_url,
        request_id=request_id,
    )


@router.post("/bkash/execute", response_model=BkashPaymentResponse)
async def execute_bkash_payment(
    request: Request,
    response: Response,
    form_data: ExecuteBkashPaymentForm,
    user=Depends(get_current_user),
    db: Session = Depends(get_session),
):
    request_id = str(uuid.uuid4())
    response.headers["X-Request-ID"] = request_id
    client = _build_bkash_client(request)
    existing = PaymentTransactions.get_by_payment_id(form_data.payment_id, db=db)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found.")
    if existing.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
    if existing.status in {"executed", "confirmed", "success", "completed"}:
        log.info(
            "bKash execute skipped request_id=%s payment_id=%s status=%s",
            request_id,
            form_data.payment_id,
            existing.status,
        )
        return BkashPaymentResponse(
            status=existing.status,
            payment_id=form_data.payment_id,
            trx_id=existing.trx_id,
            message="Payment already processed.",
            request_id=request_id,
        )
    if existing.status and "cancel" in existing.status.lower():
        return BkashPaymentResponse(
            status=existing.status,
            payment_id=form_data.payment_id,
            trx_id=existing.trx_id,
            message="Payment was canceled.",
            request_id=request_id,
        )
    if existing.status and existing.status.lower() in {"failed", "failure"}:
        return BkashPaymentResponse(
            status=existing.status,
            payment_id=form_data.payment_id,
            trx_id=existing.trx_id,
            message="Payment failed.",
            request_id=request_id,
        )

    try:
        response_data = client.execute_payment({"paymentID": form_data.payment_id})
    except HTTPError as exc:
        payload = _extract_bkash_payload(exc)
        status_value = _normalize_status(payload) if payload else None
        if status_value in {"canceled", "failed"}:
            message = _extract_bkash_message(payload)
            if not message:
                message = "Payment was canceled." if status_value == "canceled" else "Payment failed."
            updated = PaymentTransactions.update_by_payment_id(
                payment_id=form_data.payment_id,
                status=status_value,
                trx_id=payload.get("trxID") if payload else None,
                raw_response=payload or {"status": status_value, "message": message},
                db=db,
            )
            log.info(
                "bKash execute resolved request_id=%s payment_id=%s status=%s",
                request_id,
                form_data.payment_id,
                status_value,
            )
            return BkashPaymentResponse(
                status=status_value,
                payment_id=form_data.payment_id,
                trx_id=updated.trx_id if updated else None,
                message=message,
                request_id=request_id,
            )
        message, status_code = _format_bkash_http_error(exc)
        log.exception(
            "bKash execute request failed request_id=%s payment_id=%s detail=%s",
            request_id,
            form_data.payment_id,
            message,
        )
        raise HTTPException(status_code=status_code, detail=message) from exc
    except RequestException as exc:
        message = _format_bkash_request_error(exc)
        log.exception(
            "bKash execute request failed request_id=%s payment_id=%s",
            request_id,
            form_data.payment_id,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=message,
        ) from exc
    except Exception as exc:
        log.exception(
            "bKash execute request failed request_id=%s payment_id=%s",
            request_id,
            form_data.payment_id,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="bKash request failed. Please try again.",
        ) from exc
    status_value = _normalize_status(response_data)

    updated = PaymentTransactions.update_by_payment_id(
        payment_id=form_data.payment_id,
        status=status_value,
        trx_id=response_data.get("trxID"),
        raw_response=response_data,
        db=db,
    )

    log.info(
        "bKash execute request_id=%s payment_id=%s status=%s",
        request_id,
        form_data.payment_id,
        status_value,
    )
    return BkashPaymentResponse(
        status=status_value,
        payment_id=form_data.payment_id,
        trx_id=updated.trx_id if updated else None,
        message=response_data.get("statusMessage"),
        request_id=request_id,
    )


@router.get("/bkash/query", response_model=PaymentTransactionModel)
async def query_bkash_payment(
    request: Request,
    response: Response,
    payment_id: str,
    user=Depends(get_current_user),
    db: Session = Depends(get_session),
):
    request_id = str(uuid.uuid4())
    response.headers["X-Request-ID"] = request_id
    client = _build_bkash_client(request)
    existing = PaymentTransactions.get_by_payment_id(payment_id, db=db)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found.")
    if existing.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    try:
        response_data = client.query_payment(payment_id)
    except HTTPError as exc:
        message, status_code = _format_bkash_http_error(exc)
        log.exception(
            "bKash query request failed request_id=%s payment_id=%s detail=%s",
            request_id,
            payment_id,
            message,
        )
        raise HTTPException(status_code=status_code, detail=message) from exc
    except RequestException as exc:
        message = _format_bkash_request_error(exc)
        log.exception(
            "bKash query request failed request_id=%s payment_id=%s",
            request_id,
            payment_id,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=message,
        ) from exc
    except Exception as exc:
        log.exception(
            "bKash query request failed request_id=%s payment_id=%s",
            request_id,
            payment_id,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="bKash request failed. Please try again.",
        ) from exc
    status_value = _normalize_status(response_data)

    updated = PaymentTransactions.update_by_payment_id(
        payment_id=payment_id,
        status=status_value,
        trx_id=response_data.get("trxID"),
        raw_response=response_data,
        db=db,
    )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update payment.",
        )
    log.info(
        "bKash query request_id=%s payment_id=%s status=%s",
        request_id,
        payment_id,
        status_value,
    )
    return updated


async def _handle_bkash_callback(
    request: Request,
    response: Response,
    db: Session,
):
    request_id = str(uuid.uuid4())
    response.headers["X-Request-ID"] = request_id
    secret = request.app.state.config.BKASH_WEBHOOK_SECRET
    if secret and request.method == "POST":
        provided = request.headers.get("X-BKASH-WEBHOOK-SECRET")
        if provided != secret:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid signature.")

    payload = {}
    if request.method == "POST":
        try:
            payload = await request.json()
        except Exception:
            payload = {}

    query_params = dict(request.query_params)
    payment_id = (
        payload.get("paymentID")
        or payload.get("payment_id")
        or query_params.get("paymentID")
        or query_params.get("payment_id")
    )

    PaymentEvents.record_event(
        payment_id=payment_id,
        event_type="bkash_callback",
        payload={"query": query_params, "body": payload},
        db=db,
    )

    if not payment_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="paymentID is required.")

    existing = PaymentTransactions.get_by_payment_id(payment_id, db=db)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found.")

    callback_status = (
        payload.get("status")
        or payload.get("statusMessage")
        or query_params.get("status")
        or query_params.get("statusMessage")
    )
    callback_status_code = payload.get("statusCode") or query_params.get("statusCode")
    status_hint = _normalize_status(
        {"status": callback_status, "statusCode": callback_status_code}
    )
    status_message = (
        payload.get("statusMessage")
        or payload.get("status")
        or query_params.get("statusMessage")
        or query_params.get("status")
        or ""
    )
    if status_hint == "failed" and "cancel" in str(status_message).lower():
        status_hint = "canceled"
    if status_hint in {"canceled", "failed"}:
        updated = PaymentTransactions.update_by_payment_id(
            payment_id=payment_id,
            status=status_hint,
            trx_id=payload.get("trxID") or payload.get("trx_id"),
            raw_response={"query": query_params, "body": payload},
            db=db,
        )
        log.info(
            "bKash callback request_id=%s payment_id=%s status=%s",
            request_id,
            payment_id,
            status_hint,
        )
        result_payload = {
            "status": status_hint,
            "payment_id": payment_id,
            "trx_id": updated.trx_id if updated else None,
            "request_id": request_id,
        }
        if _should_redirect_callback(request):
            return RedirectResponse(
                _build_callback_redirect_url(request, payment_id, status_hint),
                status_code=status.HTTP_303_SEE_OTHER,
            )
        return result_payload

    success_statuses = {"executed", "confirmed", "success", "completed"}
    if status_hint in success_statuses:
        resolved_status = "completed" if status_hint == "success" else status_hint
        updated = PaymentTransactions.update_by_payment_id(
            payment_id=payment_id,
            status=resolved_status,
            trx_id=payload.get("trxID") or payload.get("trx_id"),
            raw_response={"query": query_params, "body": payload},
            db=db,
        )
        log.info(
            "bKash callback request_id=%s payment_id=%s status=%s",
            request_id,
            payment_id,
            resolved_status,
        )
        result_payload = {
            "status": resolved_status,
            "payment_id": payment_id,
            "trx_id": updated.trx_id if updated else None,
            "request_id": request_id,
        }
        if _should_redirect_callback(request):
            return RedirectResponse(
                _build_callback_redirect_url(request, payment_id, resolved_status),
                status_code=status.HTTP_303_SEE_OTHER,
            )
        return result_payload

    client = _build_bkash_client(request)
    try:
        response_data = client.query_payment(payment_id)
    except HTTPError as exc:
        message, status_code = _format_bkash_http_error(exc)
        log.exception(
            "bKash callback query failed request_id=%s payment_id=%s detail=%s",
            request_id,
            payment_id,
            message,
        )
        raise HTTPException(status_code=status_code, detail=message) from exc
    except RequestException as exc:
        message = _format_bkash_request_error(exc)
        log.exception(
            "bKash callback query failed request_id=%s payment_id=%s",
            request_id,
            payment_id,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=message,
        ) from exc
    except Exception as exc:
        log.exception(
            "bKash callback query failed request_id=%s payment_id=%s",
            request_id,
            payment_id,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="bKash request failed. Please try again.",
        ) from exc
    status_value = _normalize_status(response_data)

    updated = PaymentTransactions.update_by_payment_id(
        payment_id=payment_id,
        status=status_value,
        trx_id=response_data.get("trxID"),
        raw_response=response_data,
        db=db,
    )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update payment.",
        )

    log.info(
        "bKash callback request_id=%s payment_id=%s status=%s",
        request_id,
        payment_id,
        status_value,
    )
    result_payload = {
        "status": status_value,
        "payment_id": payment_id,
        "trx_id": updated.trx_id,
        "request_id": request_id,
    }
    if _should_redirect_callback(request):
        return RedirectResponse(
            _build_callback_redirect_url(request, payment_id, status_value),
            status_code=status.HTTP_303_SEE_OTHER,
        )
    return result_payload


@router.get("/bkash/callback", operation_id="bkash_callback_get")
async def bkash_callback_get(
    request: Request,
    response: Response,
    db: Session = Depends(get_session),
):
    return await _handle_bkash_callback(request, response, db)


@router.post("/bkash/callback", operation_id="bkash_callback_post")
async def bkash_callback_post(
    request: Request,
    response: Response,
    db: Session = Depends(get_session),
):
    return await _handle_bkash_callback(request, response, db)
