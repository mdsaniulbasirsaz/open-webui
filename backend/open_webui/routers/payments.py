import os
import logging
import uuid
import io
from typing import Optional
from urllib.parse import urlencode


from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from requests import HTTPError, RequestException
from requests.exceptions import ConnectionError, Timeout
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from fastapi import Query, Depends
from typing import List, Optional
from datetime import datetime
from open_webui.models.payments import PaymentTransaction, PaymentTransactionModel
from open_webui.models.payments import PaymentTransactionsResponse


from open_webui.internal.db import get_session
from open_webui.models.payments import (
    PaymentEvents,
    PaymentTransactions,
    PaymentTransactionModel,
)
from open_webui.models.users import User
from open_webui.utils.auth import get_current_user
from open_webui.utils.bkash_client import BkashClient

log = logging.getLogger(__name__)

router = APIRouter()



class UserSubscriptionDetails(BaseModel):
    has_subscription: bool
    plan_id: Optional[str] = None
    status: Optional[str] = None
    start_date: Optional[int] = None
    renewal_date: Optional[int] = None
    expiry_date: Optional[int] = None
    latest_transaction_id: Optional[str] = None
    merchant_invoice_number: Optional[str] = None
    currency: Optional[str] = None
    amount: Optional[float] = None


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


class PricingPlan(BaseModel):
    plan_id: str
    name: str
    features: str
    amount: float
    currency: str = "BDT"
    period: str = "/ month"


class PricingPlansResponse(BaseModel):
    data: List[PricingPlan]


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


# Payment Transactions Response
class PaymentTransactionsResponse(BaseModel):
    total: int
    page: int
    page_size: int
    data: List[PaymentTransactionModel]

class AdminPaymentTransactionModel(PaymentTransactionModel):
    user_email: Optional[str] = None
    user_name: Optional[str] = None
    username: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AdminPaymentTransactionsResponse(BaseModel):
    total: int
    page: int
    page_size: int
    data: List[AdminPaymentTransactionModel]

class PaymentStatusCount(BaseModel):
    status: str
    count: int


class PaymentRevenuePoint(BaseModel):
    date: str
    amount: float
    count: int


class PaymentMetricsResponse(BaseModel):
    total_amount: float
    total_transactions: int
    avg_amount: float
    currency: Optional[str] = None
    status_breakdown: List[PaymentStatusCount]
    revenue_trend: List[PaymentRevenuePoint]


class PaymentKpisResponse(BaseModel):
    mrr: float
    arr: float
    active_subscriptions: int
    arpu: float
    churn: Optional[float] = None
    currency: Optional[str] = None


class PaymentUserSummary(BaseModel):
    user_id: str
    total_amount: float
    currency: Optional[str] = None


class PaymentUsersSummaryResponse(BaseModel):
    data: List[PaymentUserSummary]


class PaymentPlanSummary(BaseModel):
    plan_id: str
    total_amount: float
    total_transactions: int
    currency: Optional[str] = None


class PaymentPlansSummaryResponse(BaseModel):
    data: List[PaymentPlanSummary]


class PaymentPlanTotalResponse(BaseModel):
    plan_id: str
    total_amount: float
    total_transactions: int
    currency: Optional[str] = None


def _apply_transaction_filters(
    query,
    user_id: Optional[str],
    status: Optional[str],
    payment_id: Optional[str],
    trx_id: Optional[str],
    merchant_invoice_number: Optional[str],
    user_query: Optional[str],
    start_date: Optional[int],
    end_date: Optional[int],
    join_user: bool = False,
):
    if user_id:
        query = query.filter(PaymentTransaction.user_id.ilike(f"%{user_id}%"))
    if status:
        query = query.filter(PaymentTransaction.status == status)
    if payment_id:
        query = query.filter(PaymentTransaction.payment_id.ilike(f"%{payment_id}%"))
    if trx_id:
        query = query.filter(PaymentTransaction.trx_id.ilike(f"%{trx_id}%"))
    if merchant_invoice_number:
        query = query.filter(
            PaymentTransaction.merchant_invoice_number.ilike(f"%{merchant_invoice_number}%")
        )
    if user_query:
        if not join_user:
            query = query.join(User, PaymentTransaction.user_id == User.id)
        query = query.filter(
            or_(
                User.email.ilike(f"%{user_query}%"),
                User.name.ilike(f"%{user_query}%"),
                User.username.ilike(f"%{user_query}%"),
            )
        )
    if start_date:
        query = query.filter(PaymentTransaction.created_at >= start_date)
    if end_date:
        query = query.filter(PaymentTransaction.created_at <= end_date)
    return query


def _estimate_subscription_window(plan_id: Optional[str], start_ts: Optional[int]) -> tuple[Optional[int], Optional[int]]:
    if not start_ts:
        return None, None

    normalized = (plan_id or "").strip().lower()
    yearly_tokens = {"year", "annual", "annually", "yr", "yearly"}
    is_yearly = any(token in normalized for token in yearly_tokens)

    duration_days = 365 if is_yearly else 30
    end_ts = start_ts + duration_days * 24 * 60 * 60
    return end_ts, end_ts


@router.get("/plans", response_model=PricingPlansResponse)
async def list_pricing_plans():
    """
    Public API to fetch pricing plans used by the UI.
    """
    plans = [
        PricingPlan(
            plan_id="free",
            name="Free",
            features="Basic Features",
            amount=0,
            currency="BDT",
            period="/ month",
        ),
        PricingPlan(
            plan_id="pro",
            name="Pro",
            features="Advanced Features",
            amount=99,
            currency="USD",
            period="/ month",
        ),
    ]

    return PricingPlansResponse(data=plans)


@router.get("/me/subscription", response_model=UserSubscriptionDetails)
async def get_my_subscription_details(
    user=Depends(get_current_user),
    db: Session = Depends(get_session),
):
    """
    User API to fetch a derived subscription summary for the current user.

    """
    latest = (
        db.query(PaymentTransaction)
        .filter(PaymentTransaction.user_id == user.id)
        .order_by(PaymentTransaction.updated_at.desc(), PaymentTransaction.created_at.desc())
        .first()
    )

    if not latest:
        return UserSubscriptionDetails(has_subscription=False)

    start_date = latest.created_at
    renewal_date, expiry_date = _estimate_subscription_window(latest.plan_id, start_date)

    return UserSubscriptionDetails(
        has_subscription=True,
        plan_id=latest.plan_id,
        status=latest.status,
        start_date=start_date,
        renewal_date=renewal_date,
        expiry_date=expiry_date,
        latest_transaction_id=latest.id,
        merchant_invoice_number=latest.merchant_invoice_number,
        currency=latest.currency,
        amount=float(latest.amount or 0),
    )


@router.get("/transactions", response_model=PaymentTransactionsResponse)
async def list_payment_transactions(
    status: Optional[str] = Query(None, description="Filter by payment status"),
    payment_id: Optional[str] = Query(None, description="Filter by Payment ID"),
    trx_id: Optional[str] = Query(None, description="Filter by transaction ID"),
    merchant_invoice_number: Optional[str] = Query(
        None, description="Filter by merchant invoice number"
    ),
    start_date: Optional[int] = Query(None, description="Filter by start date"),
    end_date: Optional[int] = Query(None, description="Filter by end date"),
    page: int = Query(1, ge=1),
    page_size: int = Query(8, ge=1, le=100),
    user=Depends(get_current_user),
    db: Session = Depends(get_session),
):
    """
    User API to fetch their payment transactions with filters and pagination.
    """
    query = db.query(PaymentTransaction).filter(PaymentTransaction.user_id == user.id)
    query = _apply_transaction_filters(
        query,
        user_id=None,
        status=status,
        payment_id=payment_id,
        trx_id=trx_id,
        merchant_invoice_number=merchant_invoice_number,
        user_query=None,
        start_date=start_date,
        end_date=end_date,
    )

    total = query.count()
    offset = (page - 1) * page_size
    records = (
        query.order_by(PaymentTransaction.created_at.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    data = [PaymentTransactionModel.model_validate(record) for record in records]

    return PaymentTransactionsResponse(
        total=total,
        page=page,
        page_size=page_size,
        data=data,
    )




@router.get("/admin/payments/transactions", response_model=AdminPaymentTransactionsResponse)
async def admin_list_payment_transactions(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    status: Optional[str] = Query(None, description="Filter by payment status"),
    payment_id: Optional[str] = Query(None, description="Filter by Payment ID"),
    trx_id: Optional[str] = Query(None, description="Filter by transaction ID"),
    merchant_invoice_number: Optional[str] = Query(
        None, description="Filter by merchant invoice number"
    ),
    user_query: Optional[str] = Query(
        None, description="Filter by user email, name, or username"
    ),
    start_date: Optional[int] = Query(None, description="Filter by start date"),
    end_date: Optional[int] = Query(None, description="Filter by end date"),
    page: int = Query(1, ge=1),
    page_size: int = Query(8, ge=1, le=100),
    db: Session = Depends(get_session),
):
    """
    Admin dashboard API to fetch payment transactions with filters, pagination, and sorting.
    """
    query = db.query(PaymentTransaction, User).outerjoin(
        User, PaymentTransaction.user_id == User.id
    )
    query = _apply_transaction_filters(
        query,
        user_id=user_id,
        status=status,
        payment_id=payment_id,
        trx_id=trx_id,
        merchant_invoice_number=merchant_invoice_number,
        user_query=user_query,
        start_date=start_date,
        end_date=end_date,
        join_user=True,
    )

    total = query.count()
    offset = (page - 1) * page_size
    records = (
        query.order_by(PaymentTransaction.created_at.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    data: List[AdminPaymentTransactionModel] = []
    for record, user in records:
        payload = PaymentTransactionModel.model_validate(record).model_dump()
        payload.update(
            {
                "user_email": getattr(user, "email", None) if user else None,
                "user_name": getattr(user, "name", None) if user else None,
                "username": getattr(user, "username", None) if user else None,
            }
        )
        data.append(AdminPaymentTransactionModel(**payload))

    return AdminPaymentTransactionsResponse(
        total=total,
        page=page,
        page_size=page_size,
        data=data,
    )


@router.get("/admin/payments/metrics", response_model=PaymentMetricsResponse)
async def admin_payment_metrics(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    status: Optional[str] = Query(None, description="Filter by payment status"),
    payment_id: Optional[str] = Query(None, description="Filter by Payment ID"),
    trx_id: Optional[str] = Query(None, description="Filter by transaction ID"),
    merchant_invoice_number: Optional[str] = Query(
        None, description="Filter by merchant invoice number"
    ),
    user_query: Optional[str] = Query(
        None, description="Filter by user email, name, or username"
    ),
    start_date: Optional[int] = Query(None, description="Filter by start date"),
    end_date: Optional[int] = Query(None, description="Filter by end date"),
    db: Session = Depends(get_session),
):
    """
    Admin dashboard API to fetch payment metrics, status breakdown, and revenue trend.
    """
    base_query = db.query(PaymentTransaction)
    base_query = _apply_transaction_filters(
        base_query,
        user_id=user_id,
        status=status,
        payment_id=payment_id,
        trx_id=trx_id,
        merchant_invoice_number=merchant_invoice_number,
        user_query=user_query,
        start_date=start_date,
        end_date=end_date,
    )

    total_transactions = base_query.count()
    total_amount = base_query.with_entities(
        func.coalesce(func.sum(PaymentTransaction.amount), 0)
    ).scalar()
    total_amount_value = float(total_amount or 0)
    avg_amount = total_amount_value / total_transactions if total_transactions else 0.0

    currency_row = (
        base_query.with_entities(PaymentTransaction.currency)
        .filter(PaymentTransaction.currency.isnot(None))
        .first()
    )
    currency = currency_row[0] if currency_row else None

    status_rows = (
        base_query.with_entities(PaymentTransaction.status, func.count(PaymentTransaction.id))
        .group_by(PaymentTransaction.status)
        .all()
    )
    status_breakdown = [
        PaymentStatusCount(status=(row[0] or "unknown"), count=row[1]) for row in status_rows
    ]

    trend_rows = base_query.with_entities(
        PaymentTransaction.created_at, PaymentTransaction.amount
    ).all()
    trend_map: dict[str, dict[str, float]] = {}
    for created_at, amount in trend_rows:
        if not created_at:
            continue
        date_key = datetime.utcfromtimestamp(created_at).strftime("%Y-%m-%d")
        bucket = trend_map.setdefault(date_key, {"amount": 0.0, "count": 0})
        amount_value = float(amount or 0)
        bucket["amount"] += amount_value
        bucket["count"] += 1

    revenue_trend = [
        PaymentRevenuePoint(date=key, amount=value["amount"], count=int(value["count"]))
        for key, value in sorted(trend_map.items())
    ]

    return PaymentMetricsResponse(
        total_amount=total_amount_value,
        total_transactions=total_transactions,
        avg_amount=avg_amount,
        currency=currency,
        status_breakdown=status_breakdown,
        revenue_trend=revenue_trend,
    )


@router.get("/admin/payments/kpis", response_model=PaymentKpisResponse)
async def admin_payment_kpis(
    start_date: Optional[int] = Query(None, description="Filter by start date"),
    end_date: Optional[int] = Query(None, description="Filter by end date"),
    db: Session = Depends(get_session),
):
    """
    Admin dashboard API to fetch KPI metrics (MRR, ARR, ARPU) for completed payments.
    """
    base_query = db.query(PaymentTransaction)
    base_query = _apply_transaction_filters(
        base_query,
        user_id=None,
        status=None,
        payment_id=None,
        trx_id=None,
        merchant_invoice_number=None,
        user_query=None,
        start_date=start_date,
        end_date=end_date,
    )

    status_value = func.trim(func.lower(PaymentTransaction.status))
    base_query = base_query.filter(status_value == "completed")

    total_transactions = base_query.with_entities(func.count(PaymentTransaction.id)).scalar()
    total_amount = base_query.with_entities(
        func.coalesce(func.sum(PaymentTransaction.amount), 0)
    ).scalar()
    total_amount_value = float(total_amount or 0)
    total_transactions_value = int(total_transactions or 0)
    arpu = (
        total_amount_value / total_transactions_value
        if total_transactions_value
        else 0.0
    )

    currency_row = (
        base_query.with_entities(PaymentTransaction.currency)
        .filter(PaymentTransaction.currency.isnot(None))
        .first()
    )
    currency = currency_row[0] if currency_row else None

    return PaymentKpisResponse(
        mrr=total_amount_value,
        arr=total_amount_value * 12,
        active_subscriptions=total_transactions_value,
        arpu=arpu,
        churn=None,
        currency=currency,
    )


@router.get("/admin/payments/users/summary", response_model=PaymentUsersSummaryResponse)
async def admin_payment_users_summary(
    user_ids: Optional[str] = Query(
        None, description="Comma-separated list of user IDs to include"
    ),
    status: Optional[str] = Query(None, description="Filter by payment status"),
    user_query: Optional[str] = Query(
        None, description="Filter by user email, name, or username"
    ),
    start_date: Optional[int] = Query(None, description="Filter by start date"),
    end_date: Optional[int] = Query(None, description="Filter by end date"),
    db: Session = Depends(get_session),
):
    """
    Admin dashboard API to fetch per-user payment totals.
    """
    query = db.query(PaymentTransaction)
    query = _apply_transaction_filters(
        query,
        user_id=None,
        status=status,
        payment_id=None,
        trx_id=None,
        merchant_invoice_number=None,
        user_query=user_query,
        start_date=start_date,
        end_date=end_date,
    )
    if user_ids:
        ids = [item.strip() for item in user_ids.split(",") if item.strip()]
        if ids:
            query = query.filter(PaymentTransaction.user_id.in_(ids))

    rows = (
        query.with_entities(
            PaymentTransaction.user_id,
            func.coalesce(func.sum(PaymentTransaction.amount), 0),
            PaymentTransaction.currency,
        )
        .group_by(PaymentTransaction.user_id, PaymentTransaction.currency)
        .all()
    )

    data = [
        PaymentUserSummary(
            user_id=row[0],
            total_amount=float(row[1] or 0),
            currency=row[2],
        )
        for row in rows
        if row[0]
    ]

    return PaymentUsersSummaryResponse(data=data)


@router.get("/admin/payments/plans/summary", response_model=PaymentPlansSummaryResponse)
async def admin_payment_plans_summary(
    start_date: Optional[int] = Query(None, description="Filter by start date"),
    end_date: Optional[int] = Query(None, description="Filter by end date"),
    db: Session = Depends(get_session),
):
    """
    Admin dashboard API to fetch per-plan payment totals for completed payments only.
    """
    completed_statuses = {"completed", "executed", "confirmed", "success"}
    status_value = func.trim(func.lower(PaymentTransaction.status))
    plan_value = func.trim(func.lower(PaymentTransaction.plan_id))
    query = db.query(PaymentTransaction).filter(status_value.in_(completed_statuses))
    query = _apply_transaction_filters(
        query,
        user_id=None,
        status=None,
        payment_id=None,
        trx_id=None,
        merchant_invoice_number=None,
        user_query=None,
        start_date=start_date,
        end_date=end_date,
    )

    rows = (
        query.with_entities(
            plan_value,
            func.coalesce(func.sum(PaymentTransaction.amount), 0),
            func.count(PaymentTransaction.id),
            PaymentTransaction.currency,
        )
        .group_by(plan_value, PaymentTransaction.currency)
        .all()
    )

    data = [
        PaymentPlanSummary(
            plan_id=row[0],
            total_amount=float(row[1] or 0),
            total_transactions=int(row[2] or 0),
            currency=row[3],
        )
        for row in rows
        if row[0]
    ]

    return PaymentPlansSummaryResponse(data=data)


@router.get("/admin/transactions/plans", response_model=PaymentPlanTotalResponse)
async def admin_plan_total_amount(
    plan_id: str = Query(..., description="Plan ID to summarize"),
    db: Session = Depends(get_session),
):
    """
    Admin API to fetch total amount for completed transactions of a plan.
    """
    normalized_plan_id = plan_id.strip().lower()
    status_value = func.trim(func.lower(PaymentTransaction.status))
    plan_value = func.trim(func.lower(PaymentTransaction.plan_id))

    query = db.query(PaymentTransaction).filter(
        status_value == "completed",
        plan_value == normalized_plan_id,
    )

    total_amount = query.with_entities(
        func.coalesce(func.sum(PaymentTransaction.amount), 0)
    ).scalar()
    total_transactions = query.with_entities(func.count(PaymentTransaction.id)).scalar()
    currency_row = (
        query.with_entities(PaymentTransaction.currency)
        .filter(PaymentTransaction.currency.isnot(None))
        .first()
    )
    currency = currency_row[0] if currency_row else None

    return PaymentPlanTotalResponse(
        plan_id=normalized_plan_id,
        total_amount=float(total_amount or 0),
        total_transactions=int(total_transactions or 0),
        currency=currency,
    )


@router.get("/admin/payments/transactions/export")
async def admin_export_payment_transactions(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    status: Optional[str] = Query(None, description="Filter by payment status"),
    payment_id: Optional[str] = Query(None, description="Filter by Payment ID"),
    trx_id: Optional[str] = Query(None, description="Filter by transaction ID"),
    merchant_invoice_number: Optional[str] = Query(
        None, description="Filter by merchant invoice number"
    ),
    user_query: Optional[str] = Query(
        None, description="Filter by user email, name, or username"
    ),
    start_date: Optional[int] = Query(None, description="Filter by start date"),
    end_date: Optional[int] = Query(None, description="Filter by end date"),
    db: Session = Depends(get_session),
):
    """
    Export payment transactions as CSV using the same filters as the admin list.
    """
    import csv
    import io

    query = db.query(PaymentTransaction, User).outerjoin(
        User, PaymentTransaction.user_id == User.id
    )
    query = _apply_transaction_filters(
        query,
        user_id=user_id,
        status=status,
        payment_id=payment_id,
        trx_id=trx_id,
        merchant_invoice_number=merchant_invoice_number,
        user_query=user_query,
        start_date=start_date,
        end_date=end_date,
        join_user=True,
    )

    records = (
        query.order_by(PaymentTransaction.created_at.desc())
        .all()
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "id",
            "user_id",
            "user_email",
            "user_name",
            "username",
            "plan_id",
            "amount",
            "currency",
            "status",
            "payment_id",
            "trx_id",
            "merchant_invoice_number",
            "created_at",
            "updated_at",
        ]
    )

    for transaction, user in records:
        writer.writerow(
            [
                transaction.id,
                transaction.user_id,
                getattr(user, "email", "") if user else "",
                getattr(user, "name", "") if user else "",
                getattr(user, "username", "") if user else "",
                transaction.plan_id or "",
                transaction.amount or "",
                transaction.currency or "",
                transaction.status or "",
                transaction.payment_id or "",
                transaction.trx_id or "",
                transaction.merchant_invoice_number or "",
                transaction.created_at,
                transaction.updated_at,
            ]
        )

    csv_value = output.getvalue()
    output.close()
    filename = f"payment-transactions-{datetime.utcnow().strftime('%Y-%m-%d')}.csv"
    return Response(
        content=csv_value,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
