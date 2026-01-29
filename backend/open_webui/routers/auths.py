import re
import uuid
import time
import datetime
import logging
from aiohttp import ClientSession
import urllib


from open_webui.models.auths import (
    AddUserForm,
    ApiKey,
    Auths,
    PasswordResetRequestForm,
    PasswordResetConfirmForm,
    Token,
    LdapForm,
    SigninForm,
    SigninResponse,
    SignupForm,
    UpdatePasswordForm,
)
from open_webui.models.users import (
    UserProfileImageResponse,
    Users,
    UpdateProfileForm,
    UserStatus,
)
from open_webui.models.groups import Groups
from open_webui.models.oauth_sessions import OAuthSessions

from open_webui.constants import ERROR_MESSAGES, WEBHOOK_MESSAGES
from open_webui.env import (
    WEBUI_AUTH,
    WEBUI_AUTH_TRUSTED_EMAIL_HEADER,
    WEBUI_AUTH_TRUSTED_NAME_HEADER,
    WEBUI_AUTH_TRUSTED_GROUPS_HEADER,
    WEBUI_AUTH_COOKIE_SAME_SITE,
    WEBUI_AUTH_COOKIE_SECURE,
    WEBUI_AUTH_SIGNOUT_REDIRECT_URL,
    ENABLE_INITIAL_ADMIN_SIGNUP,
    REQUIRE_EMAIL_VERIFICATION,
    EMAIL_VERIFICATION_OTP_TTL,
    EMAIL_VERIFICATION_OTP_LENGTH,
    EMAIL_VERIFICATION_MAX_ATTEMPTS,
    EMAIL_VERIFICATION_RESEND_COOLDOWN,
    ENABLE_EMAIL_VERIFICATION_LINK,
    EMAIL_VERIFICATION_LINK_TTL,
    EMAIL_VERIFICATION_LINK_BASE_URL,
    PASSWORD_RESET_TOKEN_TTL,
    PASSWORD_RESET_LINK_BASE_URL,
)
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import RedirectResponse, Response, JSONResponse
from open_webui.config import (
    OPENID_PROVIDER_URL,
    ENABLE_OAUTH_SIGNUP,
    ENABLE_LDAP,
    ENABLE_PASSWORD_AUTH,
)
from pydantic import BaseModel

from open_webui.utils.misc import parse_duration, validate_email_format
from open_webui.utils.auth import (
    validate_password,
    verify_password,
    decode_token,
    invalidate_token,
    create_api_key,
    create_token,
    get_admin_user,
    get_verified_user,
    get_current_user,
    get_password_hash,
    get_http_authorization_cred,
)
from open_webui.internal.db import get_session
from sqlalchemy.orm import Session
from open_webui.utils.webhook import post_webhook
from open_webui.utils.access_control import get_permissions, has_permission
from open_webui.utils.groups import apply_default_group_assignment
from open_webui.utils.email_verification import (
    generate_otp,
    hash_otp,
    verify_otp,
    generate_verification_token,
    hash_verification_token,
)
from open_webui.utils.email import (
    build_password_reset_email,
    build_password_reset_confirmation_email,
    build_signup_verification_email,
    send_email,
)
from open_webui.models.email_verifications import EmailVerifications
from open_webui.models.password_reset import PasswordResetRequests

from open_webui.utils.redis import get_redis_client
from open_webui.utils.rate_limit import RateLimiter


from typing import Optional, List, Union

from ssl import CERT_NONE, CERT_REQUIRED, PROTOCOL_TLS

from ldap3 import Server, Connection, NONE, Tls
from ldap3.utils.conv import escape_filter_chars

router = APIRouter()

log = logging.getLogger(__name__)

signin_rate_limiter = RateLimiter(
    redis_client=get_redis_client(), limit=5 * 3, window=60 * 3
)

# Separate limiters so a single request doesn't "spend" multiple increments on the same limiter.
password_reset_email_rate_limiter = RateLimiter(
    redis_client=get_redis_client(), limit=5, window=60 * 5
)
password_reset_ip_rate_limiter = RateLimiter(
    redis_client=get_redis_client(), limit=20, window=60 * 5
)
password_reset_validate_rate_limiter = RateLimiter(
    redis_client=get_redis_client(), limit=60, window=60
)
password_reset_confirm_rate_limiter = RateLimiter(
    redis_client=get_redis_client(), limit=30, window=60
)


def _get_duration_seconds(duration: str, default_seconds: int) -> int:
    try:
        parsed = parse_duration(duration)
    except Exception:
        return default_seconds
    if not parsed:
        return default_seconds
    return int(parsed.total_seconds())


async def _issue_email_verification(
    email: str,
    user_id: str,
    intended_role: str,
    disable_signup_after_verify: bool,
    webui_name: str,
    base_url: Optional[str] = None,
    db: Optional[Session] = None,
) -> int:
    otp_length = max(4, min(int(EMAIL_VERIFICATION_OTP_LENGTH), 10))
    otp = generate_otp(otp_length)
    otp_hash = hash_otp(otp)

    ttl_seconds = _get_duration_seconds(EMAIL_VERIFICATION_OTP_TTL, 15 * 60)
    now = int(time.time())
    expires_at = now + ttl_seconds

    attempts = max(1, int(EMAIL_VERIFICATION_MAX_ATTEMPTS))
    ttl_minutes = max(1, int(round(ttl_seconds / 60)))
    verification_link = None
    verification_token_hash = None
    verification_token_expires_at = None
    if ENABLE_EMAIL_VERIFICATION_LINK:
        link_base = (base_url or EMAIL_VERIFICATION_LINK_BASE_URL or "").strip()
        if link_base:
            link_base = link_base.rstrip("/")
            link_ttl_seconds = _get_duration_seconds(
                EMAIL_VERIFICATION_LINK_TTL or EMAIL_VERIFICATION_OTP_TTL,
                ttl_seconds,
            )
            verification_token = generate_verification_token()
            verification_token_hash = hash_verification_token(verification_token)
            verification_token_expires_at = now + link_ttl_seconds
            verification_link = (
                f"{link_base}/auth?"
                f"token={urllib.parse.quote(verification_token)}&"
                f"email={urllib.parse.quote(email)}"
    )
    subject, html, text = build_signup_verification_email(
        webui_name=webui_name,
        otp=otp,
        ttl_minutes=ttl_minutes,
        recipient=email,
        verification_link=verification_link,
    )
    await run_in_threadpool(send_email, email, subject, html, text)

    EmailVerifications.upsert_for_user(
        user_id=user_id,
        email=email,
        code_hash=otp_hash,
        verification_token_hash=verification_token_hash,
        verification_token_expires_at=verification_token_expires_at,
        verification_token_used_at=None,
        expires_at=expires_at,
        attempts_remaining=attempts,
        intended_role=intended_role,
        last_sent_at=now,
        disable_signup_after_verify=disable_signup_after_verify,
        db=db,
    )


async def _issue_password_reset_email(
    request: Request,
    email: str,
    user_id: str,
    webui_name: str,
    db: Session,
) -> None:
    ttl_seconds = _get_duration_seconds(PASSWORD_RESET_TOKEN_TTL, 60 * 60)
    now = int(time.time())
    expires_at = now + ttl_seconds

    token = create_token(
        data={"id": user_id, "email": email, "purpose": "password_reset"},
        expires_delta=datetime.timedelta(seconds=ttl_seconds),
    )
    token_hash = hash_verification_token(token)

    base_override = (PASSWORD_RESET_LINK_BASE_URL or "").strip()
    base_url = (
        base_override
        or (request.app.state.config.WEBUI_URL or "").strip()
        or str(request.base_url)
    )
    base_url = base_url.rstrip("/")
    reset_link = (
        f"{base_url}/auth/reset-password?"
        f"token={urllib.parse.quote(token)}&"
        f"email={urllib.parse.quote(email)}"
    )

    subject, html, text = build_password_reset_email(
        webui_name=webui_name,
        recipient=email,
        reset_link=reset_link,
        ttl_minutes=max(1, round(ttl_seconds / 60)),
    )
    await run_in_threadpool(send_email, email, subject, html, text)

    PasswordResetRequests.upsert_for_user(
        user_id=user_id,
        email=email,
        token_hash=token_hash,
        expires_at=expires_at,
        last_sent_at=now,
        db=db,
    )

    return _get_duration_seconds(EMAIL_VERIFICATION_RESEND_COOLDOWN, 60)


def _validate_password_reset_token(
    token: str, email: Optional[str], db: Session
) -> dict:
    """
    Validate that the supplied token is well-formed, matches the stored hash,
    and has not expired/been used/revoked. Returns a payload with metadata
    needed by callers (email, user_id, expires_at).
    """
    try:
        payload = decode_token(token)
    except Exception:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.INVALID_TOKEN
        )

    if payload.get("purpose") != "password_reset":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.INVALID_TOKEN
        )

    token_email = payload.get("email")
    token_user_id = payload.get("id")

    if email and token_email and email.lower() != token_email.lower():
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="The reset link email does not match the provided email.",
        )

    token_hash = hash_verification_token(token)
    record = PasswordResetRequests.get_by_token_hash(token_hash, db=db)
    if not record:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.INVALID_TOKEN
        )

    now = int(time.time())
    if record.used_at:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.LINK_ALREADY_USED
        )
    if record.revoked_at:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="This reset link has been revoked."
        )
    if record.expires_at < now:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.LINK_EXPIRED
        )

    # Ensure email alignment with record to prevent token reuse across accounts
    if email and record.email.lower() != email.lower():
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="The reset link does not belong to this email address.",
        )

    return {
        "email": record.email,
        "user_id": record.user_id or token_user_id,
        "expires_at": record.expires_at,
        "token_hash": token_hash,
    }

############################
# GetSessionUser
############################


class SessionUserResponse(Token, UserProfileImageResponse):
    expires_at: Optional[int] = None
    permissions: Optional[dict] = None


class SignupVerificationResponse(BaseModel):
    requires_email_verification: bool = True
    email: str
    resend_available_in: Optional[int] = None


class EmailVerificationForm(BaseModel):
    email: str
    otp: str


class EmailVerificationResendForm(BaseModel):
    email: str


class SessionUserInfoResponse(SessionUserResponse, UserStatus):
    bio: Optional[str] = None
    gender: Optional[str] = None
    date_of_birth: Optional[datetime.date] = None


@router.get("/", response_model=SessionUserInfoResponse)
async def get_session_user(
    request: Request,
    response: Response,
    user=Depends(get_current_user),
    db: Session = Depends(get_session),
):

    auth_header = request.headers.get("Authorization")
    auth_token = get_http_authorization_cred(auth_header)
    token = auth_token.credentials
    data = decode_token(token)

    expires_at = None

    if data:
        expires_at = data.get("exp")

        if (expires_at is not None) and int(time.time()) > expires_at:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=ERROR_MESSAGES.INVALID_TOKEN,
            )

        # Set the cookie token
        response.set_cookie(
            key="token",
            value=token,
            expires=(
                datetime.datetime.fromtimestamp(expires_at, datetime.timezone.utc)
                if expires_at
                else None
            ),
            httponly=True,  # Ensures the cookie is not accessible via JavaScript
            samesite=WEBUI_AUTH_COOKIE_SAME_SITE,
            secure=WEBUI_AUTH_COOKIE_SECURE,
        )

    user_permissions = get_permissions(
        user.id, request.app.state.config.USER_PERMISSIONS, db=db
    )

    return {
        "token": token,
        "token_type": "Bearer",
        "expires_at": expires_at,
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "role": user.role,
        "profile_image_url": user.profile_image_url,
        "bio": user.bio,
        "gender": user.gender,
        "date_of_birth": user.date_of_birth,
        "status_emoji": user.status_emoji,
        "status_message": user.status_message,
        "status_expires_at": user.status_expires_at,
        "permissions": user_permissions,
    }


############################
# Update Profile
############################


@router.post("/update/profile", response_model=UserProfileImageResponse)
async def update_profile(
    form_data: UpdateProfileForm,
    session_user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    if session_user:
        user = Users.update_user_by_id(
            session_user.id,
            form_data.model_dump(),
            db=db,
        )
        if user:
            return user
        else:
            raise HTTPException(400, detail=ERROR_MESSAGES.DEFAULT())
    else:
        raise HTTPException(400, detail=ERROR_MESSAGES.INVALID_CRED)


############################
# Update Timezone
############################


class UpdateTimezoneForm(BaseModel):
    timezone: str


@router.post("/update/timezone")
async def update_timezone(
    form_data: UpdateTimezoneForm,
    session_user=Depends(get_current_user),
    db: Session = Depends(get_session),
):
    if session_user:
        Users.update_user_by_id(
            session_user.id,
            {"timezone": form_data.timezone},
            db=db,
        )
        return {"status": True}
    else:
        raise HTTPException(400, detail=ERROR_MESSAGES.INVALID_CRED)


############################
# Update Password
############################


@router.post("/update/password", response_model=bool)
async def update_password(
    form_data: UpdatePasswordForm,
    session_user=Depends(get_current_user),
    db: Session = Depends(get_session),
):
    if WEBUI_AUTH_TRUSTED_EMAIL_HEADER:
        raise HTTPException(400, detail=ERROR_MESSAGES.ACTION_PROHIBITED)
    if session_user:
        user = Auths.authenticate_user(
            session_user.email,
            lambda pw: verify_password(form_data.password, pw),
            db=db,
        )

        if user:
            try:
                validate_password(form_data.password)
            except Exception as e:
                raise HTTPException(400, detail=str(e))
            hashed = get_password_hash(form_data.new_password)
            return Auths.update_user_password_by_id(user.id, hashed, db=db)
        else:
            raise HTTPException(400, detail=ERROR_MESSAGES.INCORRECT_PASSWORD)
    else:
        raise HTTPException(400, detail=ERROR_MESSAGES.INVALID_CRED)


############################
# LDAP Authentication
############################
@router.post("/ldap", response_model=SessionUserResponse)
async def ldap_auth(
    request: Request,
    response: Response,
    form_data: LdapForm,
    db: Session = Depends(get_session),
):
    # Security checks FIRST - before loading any config
    if not request.app.state.config.ENABLE_LDAP:
        raise HTTPException(400, detail="LDAP authentication is not enabled")

    if not ENABLE_PASSWORD_AUTH:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACTION_PROHIBITED,
        )

    # NOW load LDAP config variables
    LDAP_SERVER_LABEL = request.app.state.config.LDAP_SERVER_LABEL
    LDAP_SERVER_HOST = request.app.state.config.LDAP_SERVER_HOST
    LDAP_SERVER_PORT = request.app.state.config.LDAP_SERVER_PORT
    LDAP_ATTRIBUTE_FOR_MAIL = request.app.state.config.LDAP_ATTRIBUTE_FOR_MAIL
    LDAP_ATTRIBUTE_FOR_USERNAME = request.app.state.config.LDAP_ATTRIBUTE_FOR_USERNAME
    LDAP_SEARCH_BASE = request.app.state.config.LDAP_SEARCH_BASE
    LDAP_SEARCH_FILTERS = request.app.state.config.LDAP_SEARCH_FILTERS
    LDAP_APP_DN = request.app.state.config.LDAP_APP_DN
    LDAP_APP_PASSWORD = request.app.state.config.LDAP_APP_PASSWORD
    LDAP_USE_TLS = request.app.state.config.LDAP_USE_TLS
    LDAP_CA_CERT_FILE = request.app.state.config.LDAP_CA_CERT_FILE
    LDAP_VALIDATE_CERT = (
        CERT_REQUIRED if request.app.state.config.LDAP_VALIDATE_CERT else CERT_NONE
    )
    LDAP_CIPHERS = (
        request.app.state.config.LDAP_CIPHERS
        if request.app.state.config.LDAP_CIPHERS
        else "ALL"
    )

    try:
        tls = Tls(
            validate=LDAP_VALIDATE_CERT,
            version=PROTOCOL_TLS,
            ca_certs_file=LDAP_CA_CERT_FILE,
            ciphers=LDAP_CIPHERS,
        )
    except Exception as e:
        log.error(f"TLS configuration error: {str(e)}")
        raise HTTPException(400, detail="Failed to configure TLS for LDAP connection.")

    try:
        server = Server(
            host=LDAP_SERVER_HOST,
            port=LDAP_SERVER_PORT,
            get_info=NONE,
            use_ssl=LDAP_USE_TLS,
            tls=tls,
        )
        connection_app = Connection(
            server,
            LDAP_APP_DN,
            LDAP_APP_PASSWORD,
            auto_bind="NONE",
            authentication="SIMPLE" if LDAP_APP_DN else "ANONYMOUS",
        )
        if not connection_app.bind():
            raise HTTPException(400, detail="Application account bind failed")

        ENABLE_LDAP_GROUP_MANAGEMENT = (
            request.app.state.config.ENABLE_LDAP_GROUP_MANAGEMENT
        )
        ENABLE_LDAP_GROUP_CREATION = request.app.state.config.ENABLE_LDAP_GROUP_CREATION
        LDAP_ATTRIBUTE_FOR_GROUPS = request.app.state.config.LDAP_ATTRIBUTE_FOR_GROUPS

        search_attributes = [
            f"{LDAP_ATTRIBUTE_FOR_USERNAME}",
            f"{LDAP_ATTRIBUTE_FOR_MAIL}",
            "cn",
        ]
        if ENABLE_LDAP_GROUP_MANAGEMENT:
            search_attributes.append(f"{LDAP_ATTRIBUTE_FOR_GROUPS}")
            log.info(
                f"LDAP Group Management enabled. Adding {LDAP_ATTRIBUTE_FOR_GROUPS} to search attributes"
            )
        log.info(f"LDAP search attributes: {search_attributes}")

        search_success = connection_app.search(
            search_base=LDAP_SEARCH_BASE,
            search_filter=f"(&({LDAP_ATTRIBUTE_FOR_USERNAME}={escape_filter_chars(form_data.user.lower())}){LDAP_SEARCH_FILTERS})",
            attributes=search_attributes,
        )
        if not search_success or not connection_app.entries:
            raise HTTPException(400, detail="User not found in the LDAP server")

        entry = connection_app.entries[0]
        entry_username = entry[f"{LDAP_ATTRIBUTE_FOR_USERNAME}"].value
        email = entry[
            f"{LDAP_ATTRIBUTE_FOR_MAIL}"
        ].value  # retrieve the Attribute value

        username_list = []  # list of usernames from LDAP attribute
        if isinstance(entry_username, list):
            username_list = [str(name).lower() for name in entry_username]
        else:
            username_list = [str(entry_username).lower()]

        # TODO: support multiple emails if LDAP returns a list
        if not email:
            raise HTTPException(400, "User does not have a valid email address.")
        elif isinstance(email, str):
            email = email.lower()
        elif isinstance(email, list):
            email = email[0].lower()
        else:
            email = str(email).lower()

        cn = str(entry["cn"])  # common name
        user_dn = entry.entry_dn  # user distinguished name

        user_groups = []
        if ENABLE_LDAP_GROUP_MANAGEMENT and LDAP_ATTRIBUTE_FOR_GROUPS in entry:
            group_dns = entry[LDAP_ATTRIBUTE_FOR_GROUPS]
            log.info(f"LDAP raw group DNs for user {username_list}: {group_dns}")

            if group_dns:
                log.info(f"LDAP group_dns original: {group_dns}")
                log.info(f"LDAP group_dns type: {type(group_dns)}")
                log.info(f"LDAP group_dns length: {len(group_dns)}")

                if hasattr(group_dns, "value"):
                    group_dns = group_dns.value
                    log.info(f"Extracted .value property: {group_dns}")
                elif hasattr(group_dns, "__iter__") and not isinstance(
                    group_dns, (str, bytes)
                ):
                    group_dns = list(group_dns)
                    log.info(f"Converted to list: {group_dns}")

                if isinstance(group_dns, list):
                    group_dns = [str(item) for item in group_dns]
                else:
                    group_dns = [str(group_dns)]

                log.info(
                    f"LDAP group_dns after processing - type: {type(group_dns)}, length: {len(group_dns)}"
                )

                for group_idx, group_dn in enumerate(group_dns):
                    group_dn = str(group_dn)
                    log.info(f"Processing group DN #{group_idx + 1}: {group_dn}")

                    try:
                        group_cn = None

                        for item in group_dn.split(","):
                            item = item.strip()
                            if item.upper().startswith("CN="):
                                group_cn = item[3:]
                                break

                        if group_cn:
                            user_groups.append(group_cn)

                        else:
                            log.warning(
                                f"Could not extract CN from group DN: {group_dn}"
                            )
                    except Exception as e:
                        log.warning(
                            f"Failed to extract group name from DN {group_dn}: {e}"
                        )

                log.info(
                    f"LDAP groups for user {username_list}: {user_groups} (total: {len(user_groups)})"
                )
            else:
                log.info(f"No groups found for user {username_list}")
        elif ENABLE_LDAP_GROUP_MANAGEMENT:
            log.warning(
                f"LDAP Group Management enabled but {LDAP_ATTRIBUTE_FOR_GROUPS} attribute not found in user entry"
            )

        if username_list and form_data.user.lower() in username_list:
            connection_user = Connection(
                server,
                user_dn,
                form_data.password,
                auto_bind="NONE",
                authentication="SIMPLE",
            )
            if not connection_user.bind():
                raise HTTPException(400, "Authentication failed.")

            user = Users.get_user_by_email(email, db=db)
            if not user:
                try:
                    role = (
                        "admin"
                        if not Users.has_users(db=db)
                        else request.app.state.config.DEFAULT_USER_ROLE
                    )

                    user = Auths.insert_new_auth(
                        email=email,
                        password=str(uuid.uuid4()),
                        name=cn,
                        role=role,
                        db=db,
                    )

                    if not user:
                        raise HTTPException(
                            500, detail=ERROR_MESSAGES.CREATE_USER_ERROR
                        )

                    apply_default_group_assignment(
                        request.app.state.config.DEFAULT_GROUP_ID,
                        user.id,
                        db=db,
                    )

                except HTTPException:
                    raise
                except Exception as err:
                    log.error(f"LDAP user creation error: {str(err)}")
                    raise HTTPException(
                        500, detail="Internal error occurred during LDAP user creation."
                    )

            user = Auths.authenticate_user_by_email(email, db=db)

            if user:
                expires_delta = parse_duration(request.app.state.config.JWT_EXPIRES_IN)
                expires_at = None
                if expires_delta:
                    expires_at = int(time.time()) + int(expires_delta.total_seconds())

                token = create_token(
                    data={"id": user.id},
                    expires_delta=expires_delta,
                )

                # Set the cookie token
                response.set_cookie(
                    key="token",
                    value=token,
                    expires=(
                        datetime.datetime.fromtimestamp(
                            expires_at, datetime.timezone.utc
                        )
                        if expires_at
                        else None
                    ),
                    httponly=True,  # Ensures the cookie is not accessible via JavaScript
                    samesite=WEBUI_AUTH_COOKIE_SAME_SITE,
                    secure=WEBUI_AUTH_COOKIE_SECURE,
                )

                user_permissions = get_permissions(
                    user.id, request.app.state.config.USER_PERMISSIONS, db=db
                )

                if (
                    user.role != "admin"
                    and ENABLE_LDAP_GROUP_MANAGEMENT
                    and user_groups
                ):
                    if ENABLE_LDAP_GROUP_CREATION:
                        Groups.create_groups_by_group_names(user.id, user_groups, db=db)
                    try:
                        Groups.sync_groups_by_group_names(user.id, user_groups, db=db)
                        log.info(
                            f"Successfully synced groups for user {user.id}: {user_groups}"
                        )
                    except Exception as e:
                        log.error(f"Failed to sync groups for user {user.id}: {e}")

                return {
                    "token": token,
                    "token_type": "Bearer",
                    "expires_at": expires_at,
                    "id": user.id,
                    "email": user.email,
                    "name": user.name,
                    "role": user.role,
                    "profile_image_url": user.profile_image_url,
                    "permissions": user_permissions,
                }
            else:
                raise HTTPException(400, detail=ERROR_MESSAGES.INVALID_CRED)
        else:
            raise HTTPException(400, "User record mismatch.")
    except Exception as e:
        log.error(f"LDAP authentication error: {str(e)}")
        raise HTTPException(400, detail="LDAP authentication failed.")


############################
# SignIn
############################


@router.post("/signin", response_model=SessionUserResponse)
async def signin(
    request: Request,
    response: Response,
    form_data: SigninForm,
    db: Session = Depends(get_session),
):
    if not ENABLE_PASSWORD_AUTH:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACTION_PROHIBITED,
        )

    if WEBUI_AUTH_TRUSTED_EMAIL_HEADER:
        if WEBUI_AUTH_TRUSTED_EMAIL_HEADER not in request.headers:
            raise HTTPException(400, detail=ERROR_MESSAGES.INVALID_TRUSTED_HEADER)

        email = request.headers[WEBUI_AUTH_TRUSTED_EMAIL_HEADER].lower()
        name = email

        if WEBUI_AUTH_TRUSTED_NAME_HEADER:
            name = request.headers.get(WEBUI_AUTH_TRUSTED_NAME_HEADER, email)
            try:
                name = urllib.parse.unquote(name, encoding="utf-8")
            except Exception as e:
                pass

        if not Users.get_user_by_email(email.lower(), db=db):
            await signup(
                request,
                response,
                SignupForm(email=email, password=str(uuid.uuid4()), name=name),
                db=db,
            )

        user = Auths.authenticate_user_by_email(email, db=db)
        if WEBUI_AUTH_TRUSTED_GROUPS_HEADER and user and user.role != "admin":
            group_names = request.headers.get(
                WEBUI_AUTH_TRUSTED_GROUPS_HEADER, ""
            ).split(",")
            group_names = [name.strip() for name in group_names if name.strip()]

            if group_names:
                Groups.sync_groups_by_group_names(user.id, group_names, db=db)

    elif WEBUI_AUTH == False:
        admin_email = "admin@localhost"
        admin_password = "admin"

        if Users.get_user_by_email(admin_email.lower(), db=db):
            user = Auths.authenticate_user(
                admin_email.lower(),
                lambda pw: verify_password(admin_password, pw),
                db=db,
            )
        else:
            if Users.has_users(db=db):
                raise HTTPException(400, detail=ERROR_MESSAGES.EXISTING_USERS)

            await signup(
                request,
                response,
                SignupForm(email=admin_email, password=admin_password, name="User"),
                db=db,
            )

            user = Auths.authenticate_user(
                admin_email.lower(),
                lambda pw: verify_password(admin_password, pw),
                db=db,
            )
    else:
        if signin_rate_limiter.is_limited(form_data.email.lower()):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=ERROR_MESSAGES.RATE_LIMIT_EXCEEDED,
            )

        password_bytes = form_data.password.encode("utf-8")
        if len(password_bytes) > 72:
            # TODO: Implement other hashing algorithms that support longer passwords
            log.info("Password too long, truncating to 72 bytes for bcrypt")
            password_bytes = password_bytes[:72]

            # decode safely — ignore incomplete UTF-8 sequences
            form_data.password = password_bytes.decode("utf-8", errors="ignore")

        user = Auths.authenticate_user(
            form_data.email.lower(),
            lambda pw: verify_password(form_data.password, pw),
            db=db,
        )

    if user:
        if (
            REQUIRE_EMAIL_VERIFICATION
            and user.role == "pending"
            and EmailVerifications.get_by_email(user.email, db=db)
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "message": ERROR_MESSAGES.EMAIL_VERIFICATION_REQUIRED,
                    "requires_email_verification": True,
                    "email": user.email,
                },
            )

        expires_delta = parse_duration(request.app.state.config.JWT_EXPIRES_IN)
        expires_at = None
        if expires_delta:
            expires_at = int(time.time()) + int(expires_delta.total_seconds())

        token = create_token(
            data={"id": user.id},
            expires_delta=expires_delta,
        )

        datetime_expires_at = (
            datetime.datetime.fromtimestamp(expires_at, datetime.timezone.utc)
            if expires_at
            else None
        )

        # Set the cookie token
        response.set_cookie(
            key="token",
            value=token,
            expires=datetime_expires_at,
            httponly=True,  # Ensures the cookie is not accessible via JavaScript
            samesite=WEBUI_AUTH_COOKIE_SAME_SITE,
            secure=WEBUI_AUTH_COOKIE_SECURE,
        )

        user_permissions = get_permissions(
            user.id, request.app.state.config.USER_PERMISSIONS, db=db
        )

        return {
            "token": token,
            "token_type": "Bearer",
            "expires_at": expires_at,
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role,
            "profile_image_url": user.profile_image_url,
            "permissions": user_permissions,
        }
    else:
        raise HTTPException(400, detail=ERROR_MESSAGES.INVALID_CRED)


@router.post("/password-reset/request")
async def request_password_reset(
    request: Request,
    form_data: PasswordResetRequestForm,
    db: Session = Depends(get_session),
):
    email = form_data.email.strip().lower()
    if not validate_email_format(email):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.INVALID_EMAIL_FORMAT
        )

    client_ip = request.client.host if request.client else "unknown"
    if password_reset_email_rate_limiter.is_limited(email) or password_reset_ip_rate_limiter.is_limited(
        client_ip
    ):
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            detail=ERROR_MESSAGES.RATE_LIMIT_EXCEEDED,
        )

    user = Users.get_user_by_email(email, db=db)
    if user:
        try:
            await _issue_password_reset_email(
                request=request,
                email=email,
                user_id=user.id,
                webui_name=request.app.state.WEBUI_NAME,
                db=db,
            )
            # Avoid logging full email to reduce PII in logs; user_id + ip is enough for audits.
            log.info(f"Password reset requested for user_id={user.id}, ip={client_ip}")
        except Exception as err:
            log.error(f"Password reset request error: {err}")
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=ERROR_MESSAGES.EMAIL_DELIVERY_FAILED,
            )
    else:
        # Do not reveal whether an email exists (prevents user enumeration).
        log.info(f"Password reset requested for unknown email, ip={client_ip}")

    return {
        "message": "If we found an account for that email, you will receive password reset instructions shortly."
    }


@router.get("/password-reset/validate")
async def validate_password_reset(
    request: Request,
    token: str,
    email: Optional[str] = None,
    db: Session = Depends(get_session),
):
    client_ip = request.client.host if request.client else "unknown"
    if password_reset_validate_rate_limiter.is_limited(client_ip):
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            detail=ERROR_MESSAGES.RATE_LIMIT_EXCEEDED,
        )

    validation = _validate_password_reset_token(token, email, db)
    return {
        "valid": True,
        "expires_at": validation["expires_at"],
    }


@router.post("/password-reset/confirm")
async def confirm_password_reset(
    request: Request,
    form_data: PasswordResetConfirmForm,
    db: Session = Depends(get_session),
):
    client_ip = request.client.host if request.client else "unknown"
    if password_reset_confirm_rate_limiter.is_limited(client_ip):
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            detail=ERROR_MESSAGES.RATE_LIMIT_EXCEEDED,
        )

    validation = _validate_password_reset_token(
        form_data.token, form_data.email, db=db
    )

    try:
        validate_password(form_data.password)
    except Exception as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(e))

    user_id = validation.get("user_id")
    email = validation.get("email")

    if not user_id and email:
        user = Users.get_user_by_email(email, db=db)
        user_id = user.id if user else None

    if not user_id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.INVALID_TOKEN,
        )

    hashed = get_password_hash(form_data.password)
    updated = Auths.update_user_password_by_id(user_id, hashed, db=db)
    if not updated:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.INTERNAL_SERVER_ERROR,
        )

    PasswordResetRequests.mark_as_used(
        validation["token_hash"], used_at=int(time.time()), db=db
    )

    log.info(f"Password reset completed for user_id={user_id}, ip={client_ip}")

    try:
        subject, html, text = build_password_reset_confirmation_email(
            request.app.state.WEBUI_NAME, validation["email"]
        )
        await run_in_threadpool(send_email, validation["email"], subject, html, text)
    except Exception as err:
        log.error(f"Password reset confirmation email failed: {err}")

    return {"message": "Password updated successfully."}

############################
# SignUp
############################


@router.post(
    "/signup", response_model=Union[SessionUserResponse, SignupVerificationResponse]
)
async def signup(
    request: Request,
    response: Response,
    form_data: SignupForm,
    db: Session = Depends(get_session),
):
    has_users = Users.has_users(db=db)

    if WEBUI_AUTH:
        if (
            not request.app.state.config.ENABLE_SIGNUP
            or not request.app.state.config.ENABLE_LOGIN_FORM
        ):
            if has_users or not ENABLE_INITIAL_ADMIN_SIGNUP:
                raise HTTPException(
                    status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.ACCESS_PROHIBITED
                )
    else:
        if has_users:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.ACCESS_PROHIBITED
            )

    if not validate_email_format(form_data.email.lower()):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.INVALID_EMAIL_FORMAT
        )

    if Users.get_user_by_email(form_data.email.lower(), db=db):
        raise HTTPException(400, detail=ERROR_MESSAGES.EMAIL_TAKEN)

    try:
        try:
            validate_password(form_data.password)
        except Exception as e:
            raise HTTPException(400, detail=str(e))

        hashed = get_password_hash(form_data.password)

        intended_role = (
            "admin" if not has_users else request.app.state.config.DEFAULT_USER_ROLE
        )
        skip_verification = bool(
            WEBUI_AUTH_TRUSTED_EMAIL_HEADER
            and WEBUI_AUTH_TRUSTED_EMAIL_HEADER in request.headers
        )
        requires_verification = REQUIRE_EMAIL_VERIFICATION and not skip_verification
        disable_signup_after_verify = False
        role = intended_role

        if requires_verification:
            role = "pending"
            disable_signup_after_verify = not has_users

        user = Auths.insert_new_auth(
            form_data.email.lower(),
            hashed,
            form_data.name,
            form_data.profile_image_url,
            role,
            db=db,
        )

        if user:
            if requires_verification:
                try:
                    resend_cooldown = await _issue_email_verification(
                        email=user.email,
                        user_id=user.id,
                        intended_role=intended_role,
                        disable_signup_after_verify=disable_signup_after_verify,
                        webui_name=request.app.state.WEBUI_NAME,
                        base_url=request.app.state.config.WEBUI_URL
                        or str(request.base_url),
                        db=db,
                    )
                except Exception as err:
                    log.error(f"Email verification error: {str(err)}")
                    EmailVerifications.delete_by_email(user.email, db=db)
                    Auths.delete_auth_by_id(user.id, db=db)
                    raise HTTPException(
                        status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=ERROR_MESSAGES.EMAIL_DELIVERY_FAILED,
                    )

                return {
                    "requires_email_verification": True,
                    "email": user.email,
                    "resend_available_in": resend_cooldown,
                }

            expires_delta = parse_duration(request.app.state.config.JWT_EXPIRES_IN)
            expires_at = None
            if expires_delta:
                expires_at = int(time.time()) + int(expires_delta.total_seconds())

            token = create_token(
                data={"id": user.id},
                expires_delta=expires_delta,
            )

            datetime_expires_at = (
                datetime.datetime.fromtimestamp(expires_at, datetime.timezone.utc)
                if expires_at
                else None
            )

            # Set the cookie token
            response.set_cookie(
                key="token",
                value=token,
                expires=datetime_expires_at,
                httponly=True,  # Ensures the cookie is not accessible via JavaScript
                samesite=WEBUI_AUTH_COOKIE_SAME_SITE,
                secure=WEBUI_AUTH_COOKIE_SECURE,
            )

            if request.app.state.config.WEBHOOK_URL:
                await post_webhook(
                    request.app.state.WEBUI_NAME,
                    request.app.state.config.WEBHOOK_URL,
                    WEBHOOK_MESSAGES.USER_SIGNUP(user.name),
                    {
                        "action": "signup",
                        "message": WEBHOOK_MESSAGES.USER_SIGNUP(user.name),
                        "user": user.model_dump_json(exclude_none=True),
                    },
                )

            user_permissions = get_permissions(
                user.id, request.app.state.config.USER_PERMISSIONS, db=db
            )

            if not has_users:
                # Disable signup after the first user is created
                request.app.state.config.ENABLE_SIGNUP = False

            apply_default_group_assignment(
                request.app.state.config.DEFAULT_GROUP_ID,
                user.id,
                db=db,
            )

            return {
                "token": token,
                "token_type": "Bearer",
                "expires_at": expires_at,
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "role": user.role,
                "profile_image_url": user.profile_image_url,
                "permissions": user_permissions,
            }
        else:
            raise HTTPException(500, detail=ERROR_MESSAGES.CREATE_USER_ERROR)
    except Exception as err:
        log.error(f"Signup error: {str(err)}")
        raise HTTPException(500, detail="An internal error occurred during signup.")


@router.post("/signup/verify", response_model=SessionUserResponse)
async def verify_signup_email(
    request: Request,
    response: Response,
    form_data: EmailVerificationForm,
    db: Session = Depends(get_session),
):
    if not REQUIRE_EMAIL_VERIFICATION:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.ACTION_PROHIBITED
        )

    email = form_data.email.lower()
    if not validate_email_format(email):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.INVALID_EMAIL_FORMAT
        )
    record = EmailVerifications.get_by_email(email, db=db)
    if not record:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.EMAIL_VERIFICATION_EXPIRED
        )

    now = int(time.time())
    if record.expires_at and now > record.expires_at:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.EMAIL_VERIFICATION_EXPIRED
        )

    if record.attempts_remaining <= 0:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.EMAIL_VERIFICATION_MAX_ATTEMPTS,
        )

    if not verify_otp(form_data.otp.strip(), record.code_hash):
        remaining = EmailVerifications.decrement_attempts(email, db=db)
        if remaining is not None and remaining <= 0:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.EMAIL_VERIFICATION_MAX_ATTEMPTS,
            )
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.EMAIL_VERIFICATION_INVALID
        )

    user = Users.get_user_by_email(email, db=db)
    if not user:
        EmailVerifications.delete_by_email(email, db=db)
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.USER_NOT_FOUND
        )

    Users.update_user_role_by_id(user.id, record.intended_role, db=db)
    EmailVerifications.delete_by_email(email, db=db)

    if record.disable_signup_after_verify:
        request.app.state.config.ENABLE_SIGNUP = False

    apply_default_group_assignment(
        request.app.state.config.DEFAULT_GROUP_ID,
        user.id,
        db=db,
    )

    expires_delta = parse_duration(request.app.state.config.JWT_EXPIRES_IN)
    expires_at = None
    if expires_delta:
        expires_at = int(time.time()) + int(expires_delta.total_seconds())

    token = create_token(
        data={"id": user.id},
        expires_delta=expires_delta,
    )

    datetime_expires_at = (
        datetime.datetime.fromtimestamp(expires_at, datetime.timezone.utc)
        if expires_at
        else None
    )

    response.set_cookie(
        key="token",
        value=token,
        expires=datetime_expires_at,
        httponly=True,
        samesite=WEBUI_AUTH_COOKIE_SAME_SITE,
        secure=WEBUI_AUTH_COOKIE_SECURE,
    )

    user_permissions = get_permissions(
        user.id, request.app.state.config.USER_PERMISSIONS, db=db
    )

    return {
        "token": token,
        "token_type": "Bearer",
        "expires_at": expires_at,
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "role": record.intended_role,
        "profile_image_url": user.profile_image_url,
        "permissions": user_permissions,
    }


async def _verify_signup_email_link(
    request: Request,
    response: Response,
    token: str,
    db: Session,
    email: Optional[str] = None,
):
    if not REQUIRE_EMAIL_VERIFICATION:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.ACTION_PROHIBITED
        )

    token = token.strip() if token else ""
    if not token:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.EMAIL_VERIFICATION_INVALID
        )

    token_hash = hash_verification_token(token)
    record = EmailVerifications.get_by_token_hash(token_hash, db=db)
    if not record:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.EMAIL_VERIFICATION_EXPIRED
        )

    if email:
        email = email.lower()
        if not validate_email_format(email):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.INVALID_EMAIL_FORMAT
            )
        if record.email != email:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.EMAIL_VERIFICATION_EXPIRED,
            )

    now = int(time.time())
    token_expires_at = record.verification_token_expires_at or record.expires_at
    if record.verification_token_used_at:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.EMAIL_VERIFICATION_EXPIRED
        )
    if token_expires_at and now > token_expires_at:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.EMAIL_VERIFICATION_EXPIRED
        )

    user = Users.get_user_by_email(record.email, db=db)
    if not user:
        EmailVerifications.delete_by_email(record.email, db=db)
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.USER_NOT_FOUND
        )

    Users.update_user_role_by_id(user.id, record.intended_role, db=db)
    EmailVerifications.delete_by_email(record.email, db=db)

    if record.disable_signup_after_verify:
        request.app.state.config.ENABLE_SIGNUP = False

    apply_default_group_assignment(
        request.app.state.config.DEFAULT_GROUP_ID,
        user.id,
        db=db,
    )

    expires_delta = parse_duration(request.app.state.config.JWT_EXPIRES_IN)
    expires_at = None
    if expires_delta:
        expires_at = int(time.time()) + int(expires_delta.total_seconds())

    token = create_token(
        data={"id": user.id},
        expires_delta=expires_delta,
    )

    datetime_expires_at = (
        datetime.datetime.fromtimestamp(expires_at, datetime.timezone.utc)
        if expires_at
        else None
    )

    response.set_cookie(
        key="token",
        value=token,
        expires=datetime_expires_at,
        httponly=True,
        samesite=WEBUI_AUTH_COOKIE_SAME_SITE,
        secure=WEBUI_AUTH_COOKIE_SECURE,
    )

    user_permissions = get_permissions(
        user.id, request.app.state.config.USER_PERMISSIONS, db=db
    )

    return {
        "token": token,
        "token_type": "Bearer",
        "expires_at": expires_at,
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "role": record.intended_role,
        "profile_image_url": user.profile_image_url,
        "permissions": user_permissions,
    }


@router.get("/signup/verify/link", response_model=SessionUserResponse)
async def verify_signup_email_link(
    request: Request,
    response: Response,
    token: str,
    email: Optional[str] = None,
    db: Session = Depends(get_session),
):
    return await _verify_signup_email_link(
        request=request,
        response=response,
        token=token,
        email=email,
        db=db,
    )


@router.get("/verify-email/link", response_model=SessionUserResponse)
async def verify_email_link(
    request: Request,
    response: Response,
    token: str,
    email: Optional[str] = None,
    db: Session = Depends(get_session),
):
    return await _verify_signup_email_link(
        request=request,
        response=response,
        token=token,
        email=email,
        db=db,
    )


@router.post("/signup/resend")
async def resend_signup_email(
    request: Request,
    form_data: EmailVerificationResendForm,
    db: Session = Depends(get_session),
):
    if not REQUIRE_EMAIL_VERIFICATION:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.ACTION_PROHIBITED
        )

    email = form_data.email.lower()
    if not validate_email_format(email):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.INVALID_EMAIL_FORMAT
        )
    record = EmailVerifications.get_by_email(email, db=db)
    if not record:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.EMAIL_VERIFICATION_EXPIRED
        )

    cooldown_seconds = _get_duration_seconds(EMAIL_VERIFICATION_RESEND_COOLDOWN, 60)
    now = int(time.time())
    if record.last_sent_at and (now - record.last_sent_at) < cooldown_seconds:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            detail=ERROR_MESSAGES.EMAIL_VERIFICATION_RESEND_COOLDOWN,
        )

    try:
        resend_cooldown = await _issue_email_verification(
            email=email,
            user_id=record.user_id,
            intended_role=record.intended_role,
            disable_signup_after_verify=record.disable_signup_after_verify,
            webui_name=request.app.state.WEBUI_NAME,
            base_url=request.app.state.config.WEBUI_URL or str(request.base_url),
            db=db,
        )
    except Exception as err:
        log.error(f"Email verification resend error: {str(err)}")
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.EMAIL_DELIVERY_FAILED,
        )

    return {"status": True, "resend_available_in": resend_cooldown}


@router.get("/signout")
async def signout(
    request: Request, response: Response, db: Session = Depends(get_session)
):

    # get auth token from headers or cookies
    token = None
    auth_header = request.headers.get("Authorization")
    if auth_header:
        auth_cred = get_http_authorization_cred(auth_header)
        token = auth_cred.credentials
    else:
        token = request.cookies.get("token")

    if token:
        await invalidate_token(request, token)

    response.delete_cookie("token")
    response.delete_cookie("oui-session")
    response.delete_cookie("oauth_id_token")

    oauth_session_id = request.cookies.get("oauth_session_id")
    if oauth_session_id:
        response.delete_cookie("oauth_session_id")

        session = OAuthSessions.get_session_by_id(oauth_session_id, db=db)
        oauth_server_metadata_url = (
            request.app.state.oauth_manager.get_server_metadata_url(session.provider)
            if session
            else None
        ) or OPENID_PROVIDER_URL.value

        if session and oauth_server_metadata_url:
            oauth_id_token = session.token.get("id_token")
            try:
                async with ClientSession(trust_env=True) as session:
                    async with session.get(oauth_server_metadata_url) as r:
                        if r.status == 200:
                            openid_data = await r.json()
                            logout_url = openid_data.get("end_session_endpoint")

                            if logout_url:
                                return JSONResponse(
                                    status_code=200,
                                    content={
                                        "status": True,
                                        "redirect_url": f"{logout_url}?id_token_hint={oauth_id_token}"
                                        + (
                                            f"&post_logout_redirect_uri={WEBUI_AUTH_SIGNOUT_REDIRECT_URL}"
                                            if WEBUI_AUTH_SIGNOUT_REDIRECT_URL
                                            else ""
                                        ),
                                    },
                                    headers=response.headers,
                                )
                        else:
                            raise Exception("Failed to fetch OpenID configuration")

            except Exception as e:
                log.error(f"OpenID signout error: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to sign out from the OpenID provider.",
                    headers=response.headers,
                )

    if WEBUI_AUTH_SIGNOUT_REDIRECT_URL:
        return JSONResponse(
            status_code=200,
            content={
                "status": True,
                "redirect_url": WEBUI_AUTH_SIGNOUT_REDIRECT_URL,
            },
            headers=response.headers,
        )

    return JSONResponse(
        status_code=200, content={"status": True}, headers=response.headers
    )


############################
# AddUser
############################


@router.post("/add", response_model=SigninResponse)
async def add_user(
    request: Request,
    form_data: AddUserForm,
    user=Depends(get_admin_user),
    db: Session = Depends(get_session),
):
    if not validate_email_format(form_data.email.lower()):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.INVALID_EMAIL_FORMAT
        )

    if Users.get_user_by_email(form_data.email.lower(), db=db):
        raise HTTPException(400, detail=ERROR_MESSAGES.EMAIL_TAKEN)

    try:
        try:
            validate_password(form_data.password)
        except Exception as e:
            raise HTTPException(400, detail=str(e))

        hashed = get_password_hash(form_data.password)
        user = Auths.insert_new_auth(
            form_data.email.lower(),
            hashed,
            form_data.name,
            form_data.profile_image_url,
            form_data.role,
            db=db,
        )

        if user:
            apply_default_group_assignment(
                request.app.state.config.DEFAULT_GROUP_ID,
                user.id,
                db=db,
            )

            token = create_token(data={"id": user.id})
            return {
                "token": token,
                "token_type": "Bearer",
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "role": user.role,
                "profile_image_url": user.profile_image_url,
            }
        else:
            raise HTTPException(500, detail=ERROR_MESSAGES.CREATE_USER_ERROR)
    except Exception as err:
        log.error(f"Add user error: {str(err)}")
        raise HTTPException(
            500, detail="An internal error occurred while adding the user."
        )


############################
# GetAdminDetails
############################


@router.get("/admin/details")
async def get_admin_details(
    request: Request, user=Depends(get_current_user), db: Session = Depends(get_session)
):
    if request.app.state.config.SHOW_ADMIN_DETAILS:
        admin_email = request.app.state.config.ADMIN_EMAIL
        admin_name = None

        log.info(f"Admin details - Email: {admin_email}, Name: {admin_name}")

        if admin_email:
            admin = Users.get_user_by_email(admin_email, db=db)
            if admin:
                admin_name = admin.name
        else:
            admin = Users.get_first_user(db=db)
            if admin:
                admin_email = admin.email
                admin_name = admin.name

        return {
            "name": admin_name,
            "email": admin_email,
        }
    else:
        raise HTTPException(400, detail=ERROR_MESSAGES.ACTION_PROHIBITED)


############################
# ToggleSignUp
############################


@router.get("/admin/config")
async def get_admin_config(request: Request, user=Depends(get_admin_user)):
    return {
        "SHOW_ADMIN_DETAILS": request.app.state.config.SHOW_ADMIN_DETAILS,
        "ADMIN_EMAIL": request.app.state.config.ADMIN_EMAIL,
        "WEBUI_URL": request.app.state.config.WEBUI_URL,
        "ENABLE_SIGNUP": request.app.state.config.ENABLE_SIGNUP,
        "ENABLE_API_KEYS": request.app.state.config.ENABLE_API_KEYS,
        "ENABLE_API_KEYS_ENDPOINT_RESTRICTIONS": request.app.state.config.ENABLE_API_KEYS_ENDPOINT_RESTRICTIONS,
        "API_KEYS_ALLOWED_ENDPOINTS": request.app.state.config.API_KEYS_ALLOWED_ENDPOINTS,
        "DEFAULT_USER_ROLE": request.app.state.config.DEFAULT_USER_ROLE,
        "DEFAULT_GROUP_ID": request.app.state.config.DEFAULT_GROUP_ID,
        "JWT_EXPIRES_IN": request.app.state.config.JWT_EXPIRES_IN,
        "ENABLE_COMMUNITY_SHARING": request.app.state.config.ENABLE_COMMUNITY_SHARING,
        "ENABLE_MESSAGE_RATING": request.app.state.config.ENABLE_MESSAGE_RATING,
        "ENABLE_FOLDERS": request.app.state.config.ENABLE_FOLDERS,
        "FOLDER_MAX_FILE_COUNT": request.app.state.config.FOLDER_MAX_FILE_COUNT,
        "ENABLE_CHANNELS": request.app.state.config.ENABLE_CHANNELS,
        "ENABLE_MEMORIES": request.app.state.config.ENABLE_MEMORIES,
        "ENABLE_NOTES": request.app.state.config.ENABLE_NOTES,
        "ENABLE_USER_WEBHOOKS": request.app.state.config.ENABLE_USER_WEBHOOKS,
        "ENABLE_USER_STATUS": request.app.state.config.ENABLE_USER_STATUS,
        "PENDING_USER_OVERLAY_TITLE": request.app.state.config.PENDING_USER_OVERLAY_TITLE,
        "PENDING_USER_OVERLAY_CONTENT": request.app.state.config.PENDING_USER_OVERLAY_CONTENT,
        "RESPONSE_WATERMARK": request.app.state.config.RESPONSE_WATERMARK,
    }


class AdminConfig(BaseModel):
    SHOW_ADMIN_DETAILS: bool
    ADMIN_EMAIL: Optional[str] = None
    WEBUI_URL: str
    ENABLE_SIGNUP: bool
    ENABLE_API_KEYS: bool
    ENABLE_API_KEYS_ENDPOINT_RESTRICTIONS: bool
    API_KEYS_ALLOWED_ENDPOINTS: str
    DEFAULT_USER_ROLE: str
    DEFAULT_GROUP_ID: str
    JWT_EXPIRES_IN: str
    ENABLE_COMMUNITY_SHARING: bool
    ENABLE_MESSAGE_RATING: bool
    ENABLE_FOLDERS: bool
    FOLDER_MAX_FILE_COUNT: Optional[int | str] = None
    ENABLE_CHANNELS: bool
    ENABLE_MEMORIES: bool
    ENABLE_NOTES: bool
    ENABLE_USER_WEBHOOKS: bool
    ENABLE_USER_STATUS: bool
    PENDING_USER_OVERLAY_TITLE: Optional[str] = None
    PENDING_USER_OVERLAY_CONTENT: Optional[str] = None
    RESPONSE_WATERMARK: Optional[str] = None


@router.post("/admin/config")
async def update_admin_config(
    request: Request, form_data: AdminConfig, user=Depends(get_admin_user)
):
    request.app.state.config.SHOW_ADMIN_DETAILS = form_data.SHOW_ADMIN_DETAILS
    request.app.state.config.ADMIN_EMAIL = form_data.ADMIN_EMAIL
    request.app.state.config.WEBUI_URL = form_data.WEBUI_URL
    request.app.state.config.ENABLE_SIGNUP = form_data.ENABLE_SIGNUP

    request.app.state.config.ENABLE_API_KEYS = form_data.ENABLE_API_KEYS
    request.app.state.config.ENABLE_API_KEYS_ENDPOINT_RESTRICTIONS = (
        form_data.ENABLE_API_KEYS_ENDPOINT_RESTRICTIONS
    )
    request.app.state.config.API_KEYS_ALLOWED_ENDPOINTS = (
        form_data.API_KEYS_ALLOWED_ENDPOINTS
    )

    request.app.state.config.ENABLE_FOLDERS = form_data.ENABLE_FOLDERS
    request.app.state.config.FOLDER_MAX_FILE_COUNT = (
        int(form_data.FOLDER_MAX_FILE_COUNT) if form_data.FOLDER_MAX_FILE_COUNT else ""
    )
    request.app.state.config.ENABLE_CHANNELS = form_data.ENABLE_CHANNELS
    request.app.state.config.ENABLE_MEMORIES = form_data.ENABLE_MEMORIES
    request.app.state.config.ENABLE_NOTES = form_data.ENABLE_NOTES

    if form_data.DEFAULT_USER_ROLE in ["pending", "user", "admin"]:
        request.app.state.config.DEFAULT_USER_ROLE = form_data.DEFAULT_USER_ROLE

    request.app.state.config.DEFAULT_GROUP_ID = form_data.DEFAULT_GROUP_ID

    pattern = r"^(-1|0|(-?\d+(\.\d+)?)(ms|s|m|h|d|w))$"

    # Check if the input string matches the pattern
    if re.match(pattern, form_data.JWT_EXPIRES_IN):
        request.app.state.config.JWT_EXPIRES_IN = form_data.JWT_EXPIRES_IN

    request.app.state.config.ENABLE_COMMUNITY_SHARING = (
        form_data.ENABLE_COMMUNITY_SHARING
    )
    request.app.state.config.ENABLE_MESSAGE_RATING = form_data.ENABLE_MESSAGE_RATING

    request.app.state.config.ENABLE_USER_WEBHOOKS = form_data.ENABLE_USER_WEBHOOKS
    request.app.state.config.ENABLE_USER_STATUS = form_data.ENABLE_USER_STATUS

    request.app.state.config.PENDING_USER_OVERLAY_TITLE = (
        form_data.PENDING_USER_OVERLAY_TITLE
    )
    request.app.state.config.PENDING_USER_OVERLAY_CONTENT = (
        form_data.PENDING_USER_OVERLAY_CONTENT
    )

    request.app.state.config.RESPONSE_WATERMARK = form_data.RESPONSE_WATERMARK

    return {
        "SHOW_ADMIN_DETAILS": request.app.state.config.SHOW_ADMIN_DETAILS,
        "ADMIN_EMAIL": request.app.state.config.ADMIN_EMAIL,
        "WEBUI_URL": request.app.state.config.WEBUI_URL,
        "ENABLE_SIGNUP": request.app.state.config.ENABLE_SIGNUP,
        "ENABLE_API_KEYS": request.app.state.config.ENABLE_API_KEYS,
        "ENABLE_API_KEYS_ENDPOINT_RESTRICTIONS": request.app.state.config.ENABLE_API_KEYS_ENDPOINT_RESTRICTIONS,
        "API_KEYS_ALLOWED_ENDPOINTS": request.app.state.config.API_KEYS_ALLOWED_ENDPOINTS,
        "DEFAULT_USER_ROLE": request.app.state.config.DEFAULT_USER_ROLE,
        "DEFAULT_GROUP_ID": request.app.state.config.DEFAULT_GROUP_ID,
        "JWT_EXPIRES_IN": request.app.state.config.JWT_EXPIRES_IN,
        "ENABLE_COMMUNITY_SHARING": request.app.state.config.ENABLE_COMMUNITY_SHARING,
        "ENABLE_MESSAGE_RATING": request.app.state.config.ENABLE_MESSAGE_RATING,
        "ENABLE_FOLDERS": request.app.state.config.ENABLE_FOLDERS,
        "FOLDER_MAX_FILE_COUNT": request.app.state.config.FOLDER_MAX_FILE_COUNT,
        "ENABLE_CHANNELS": request.app.state.config.ENABLE_CHANNELS,
        "ENABLE_MEMORIES": request.app.state.config.ENABLE_MEMORIES,
        "ENABLE_NOTES": request.app.state.config.ENABLE_NOTES,
        "ENABLE_USER_WEBHOOKS": request.app.state.config.ENABLE_USER_WEBHOOKS,
        "ENABLE_USER_STATUS": request.app.state.config.ENABLE_USER_STATUS,
        "PENDING_USER_OVERLAY_TITLE": request.app.state.config.PENDING_USER_OVERLAY_TITLE,
        "PENDING_USER_OVERLAY_CONTENT": request.app.state.config.PENDING_USER_OVERLAY_CONTENT,
        "RESPONSE_WATERMARK": request.app.state.config.RESPONSE_WATERMARK,
    }


class LdapServerConfig(BaseModel):
    label: str
    host: str
    port: Optional[int] = None
    attribute_for_mail: str = "mail"
    attribute_for_username: str = "uid"
    app_dn: str
    app_dn_password: str
    search_base: str
    search_filters: str = ""
    use_tls: bool = True
    certificate_path: Optional[str] = None
    validate_cert: bool = True
    ciphers: Optional[str] = "ALL"


@router.get("/admin/config/ldap/server", response_model=LdapServerConfig)
async def get_ldap_server(request: Request, user=Depends(get_admin_user)):
    return {
        "label": request.app.state.config.LDAP_SERVER_LABEL,
        "host": request.app.state.config.LDAP_SERVER_HOST,
        "port": request.app.state.config.LDAP_SERVER_PORT,
        "attribute_for_mail": request.app.state.config.LDAP_ATTRIBUTE_FOR_MAIL,
        "attribute_for_username": request.app.state.config.LDAP_ATTRIBUTE_FOR_USERNAME,
        "app_dn": request.app.state.config.LDAP_APP_DN,
        "app_dn_password": request.app.state.config.LDAP_APP_PASSWORD,
        "search_base": request.app.state.config.LDAP_SEARCH_BASE,
        "search_filters": request.app.state.config.LDAP_SEARCH_FILTERS,
        "use_tls": request.app.state.config.LDAP_USE_TLS,
        "certificate_path": request.app.state.config.LDAP_CA_CERT_FILE,
        "validate_cert": request.app.state.config.LDAP_VALIDATE_CERT,
        "ciphers": request.app.state.config.LDAP_CIPHERS,
    }


@router.post("/admin/config/ldap/server")
async def update_ldap_server(
    request: Request, form_data: LdapServerConfig, user=Depends(get_admin_user)
):
    required_fields = [
        "label",
        "host",
        "attribute_for_mail",
        "attribute_for_username",
        "app_dn",
        "app_dn_password",
        "search_base",
    ]
    for key in required_fields:
        value = getattr(form_data, key)
        if not value:
            raise HTTPException(400, detail=f"Required field {key} is empty")

    request.app.state.config.LDAP_SERVER_LABEL = form_data.label
    request.app.state.config.LDAP_SERVER_HOST = form_data.host
    request.app.state.config.LDAP_SERVER_PORT = form_data.port
    request.app.state.config.LDAP_ATTRIBUTE_FOR_MAIL = form_data.attribute_for_mail
    request.app.state.config.LDAP_ATTRIBUTE_FOR_USERNAME = (
        form_data.attribute_for_username
    )
    request.app.state.config.LDAP_APP_DN = form_data.app_dn
    request.app.state.config.LDAP_APP_PASSWORD = form_data.app_dn_password
    request.app.state.config.LDAP_SEARCH_BASE = form_data.search_base
    request.app.state.config.LDAP_SEARCH_FILTERS = form_data.search_filters
    request.app.state.config.LDAP_USE_TLS = form_data.use_tls
    request.app.state.config.LDAP_CA_CERT_FILE = form_data.certificate_path
    request.app.state.config.LDAP_VALIDATE_CERT = form_data.validate_cert
    request.app.state.config.LDAP_CIPHERS = form_data.ciphers

    return {
        "label": request.app.state.config.LDAP_SERVER_LABEL,
        "host": request.app.state.config.LDAP_SERVER_HOST,
        "port": request.app.state.config.LDAP_SERVER_PORT,
        "attribute_for_mail": request.app.state.config.LDAP_ATTRIBUTE_FOR_MAIL,
        "attribute_for_username": request.app.state.config.LDAP_ATTRIBUTE_FOR_USERNAME,
        "app_dn": request.app.state.config.LDAP_APP_DN,
        "app_dn_password": request.app.state.config.LDAP_APP_PASSWORD,
        "search_base": request.app.state.config.LDAP_SEARCH_BASE,
        "search_filters": request.app.state.config.LDAP_SEARCH_FILTERS,
        "use_tls": request.app.state.config.LDAP_USE_TLS,
        "certificate_path": request.app.state.config.LDAP_CA_CERT_FILE,
        "validate_cert": request.app.state.config.LDAP_VALIDATE_CERT,
        "ciphers": request.app.state.config.LDAP_CIPHERS,
    }


@router.get("/admin/config/ldap")
async def get_ldap_config(request: Request, user=Depends(get_admin_user)):
    return {"ENABLE_LDAP": request.app.state.config.ENABLE_LDAP}


class LdapConfigForm(BaseModel):
    enable_ldap: Optional[bool] = None


@router.post("/admin/config/ldap")
async def update_ldap_config(
    request: Request, form_data: LdapConfigForm, user=Depends(get_admin_user)
):
    request.app.state.config.ENABLE_LDAP = form_data.enable_ldap
    return {"ENABLE_LDAP": request.app.state.config.ENABLE_LDAP}


############################
# API Key
############################


# create api key
@router.post("/api_key", response_model=ApiKey)
async def generate_api_key(
    request: Request, user=Depends(get_current_user), db: Session = Depends(get_session)
):
    if not request.app.state.config.ENABLE_API_KEYS or not has_permission(
        user.id, "features.api_keys", request.app.state.config.USER_PERMISSIONS
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.API_KEY_CREATION_NOT_ALLOWED,
        )

    api_key = create_api_key()
    success = Users.update_user_api_key_by_id(user.id, api_key, db=db)

    if success:
        return {
            "api_key": api_key,
        }
    else:
        raise HTTPException(500, detail=ERROR_MESSAGES.CREATE_API_KEY_ERROR)


# delete api key
@router.delete("/api_key", response_model=bool)
async def delete_api_key(
    user=Depends(get_current_user), db: Session = Depends(get_session)
):
    return Users.delete_user_api_key_by_id(user.id, db=db)


# get api key
@router.get("/api_key", response_model=ApiKey)
async def get_api_key(
    user=Depends(get_current_user), db: Session = Depends(get_session)
):
    api_key = Users.get_user_api_key_by_id(user.id, db=db)
    if api_key:
        return {
            "api_key": api_key,
        }
    else:
        raise HTTPException(404, detail=ERROR_MESSAGES.API_KEY_NOT_FOUND)
