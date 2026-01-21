import time

from open_webui.models.email_verifications import EmailVerifications
from open_webui.utils.auth import get_password_hash
from open_webui.utils.email_verification import (
    generate_verification_token,
    hash_otp,
    hash_verification_token,
)
from test.util.abstract_integration_test import AbstractPostgresTest
from test.util.mock_user import mock_webui_user


class TestAuths(AbstractPostgresTest):
    BASE_PATH = "/api/v1/auths"

    def setup_class(cls):
        super().setup_class()
        from open_webui.models.auths import Auths
        from open_webui.models.users import Users

        cls.users = Users
        cls.auths = Auths

    def _create_email_verification_record(
        self,
        user,
        otp: str,
        token: str,
        now: int,
        token_expires_at: int | None = None,
        otp_expires_at: int | None = None,
        last_sent_at: int | None = None,
    ):
        EmailVerifications.upsert_for_user(
            user_id=user.id,
            email=user.email,
            code_hash=hash_otp(otp),
            verification_token_hash=hash_verification_token(token),
            verification_token_expires_at=token_expires_at or (now + 300),
            verification_token_used_at=None,
            expires_at=otp_expires_at or (now + 300),
            attempts_remaining=3,
            intended_role="user",
            last_sent_at=last_sent_at if last_sent_at is not None else now,
            disable_signup_after_verify=False,
        )

    def test_get_session_user(self):
        with mock_webui_user():
            response = self.fast_api_client.get(self.create_url(""))
        assert response.status_code == 200
        assert response.json() == {
            "id": "1",
            "name": "John Doe",
            "email": "john.doe@openwebui.com",
            "role": "user",
            "profile_image_url": "/user.png",
        }

    def test_update_profile(self):
        user = self.auths.insert_new_auth(
            email="john.doe@openwebui.com",
            password=get_password_hash("old_password"),
            name="John Doe",
            profile_image_url="/user.png",
            role="user",
        )

        with mock_webui_user(id=user.id):
            response = self.fast_api_client.post(
                self.create_url("/update/profile"),
                json={"name": "John Doe 2", "profile_image_url": "/user2.png"},
            )
        assert response.status_code == 200
        db_user = self.users.get_user_by_id(user.id)
        assert db_user.name == "John Doe 2"
        assert db_user.profile_image_url == "/user2.png"

    def test_update_password(self):
        user = self.auths.insert_new_auth(
            email="john.doe@openwebui.com",
            password=get_password_hash("old_password"),
            name="John Doe",
            profile_image_url="/user.png",
            role="user",
        )

        with mock_webui_user(id=user.id):
            response = self.fast_api_client.post(
                self.create_url("/update/password"),
                json={"password": "old_password", "new_password": "new_password"},
            )
        assert response.status_code == 200

        old_auth = self.auths.authenticate_user(
            "john.doe@openwebui.com", "old_password"
        )
        assert old_auth is None
        new_auth = self.auths.authenticate_user(
            "john.doe@openwebui.com", "new_password"
        )
        assert new_auth is not None

    def test_signin(self):
        user = self.auths.insert_new_auth(
            email="john.doe@openwebui.com",
            password=get_password_hash("password"),
            name="John Doe",
            profile_image_url="/user.png",
            role="user",
        )
        response = self.fast_api_client.post(
            self.create_url("/signin"),
            json={"email": "john.doe@openwebui.com", "password": "password"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == user.id
        assert data["name"] == "John Doe"
        assert data["email"] == "john.doe@openwebui.com"
        assert data["role"] == "user"
        assert data["profile_image_url"] == "/user.png"
        assert data["token"] is not None and len(data["token"]) > 0
        assert data["token_type"] == "Bearer"

    def test_signup(self):
        response = self.fast_api_client.post(
            self.create_url("/signup"),
            json={
                "name": "John Doe",
                "email": "john.doe@openwebui.com",
                "password": "password",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] is not None and len(data["id"]) > 0
        assert data["name"] == "John Doe"
        assert data["email"] == "john.doe@openwebui.com"
        assert data["role"] in ["admin", "user", "pending"]
        assert data["profile_image_url"] == "/user.png"
        assert data["token"] is not None and len(data["token"]) > 0
        assert data["token_type"] == "Bearer"

    def test_add_user(self):
        with mock_webui_user():
            response = self.fast_api_client.post(
                self.create_url("/add"),
                json={
                    "name": "John Doe 2",
                    "email": "john.doe2@openwebui.com",
                    "password": "password2",
                    "role": "admin",
                },
            )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] is not None and len(data["id"]) > 0
        assert data["name"] == "John Doe 2"
        assert data["email"] == "john.doe2@openwebui.com"
        assert data["role"] == "admin"
        assert data["profile_image_url"] == "/user.png"
        assert data["token"] is not None and len(data["token"]) > 0
        assert data["token_type"] == "Bearer"

    def test_get_admin_details(self):
        self.auths.insert_new_auth(
            email="john.doe@openwebui.com",
            password="password",
            name="John Doe",
            profile_image_url="/user.png",
            role="admin",
        )
        with mock_webui_user():
            response = self.fast_api_client.get(self.create_url("/admin/details"))

        assert response.status_code == 200
        assert response.json() == {
            "name": "John Doe",
            "email": "john.doe@openwebui.com",
        }

    def test_create_api_key_(self):
        user = self.auths.insert_new_auth(
            email="john.doe@openwebui.com",
            password="password",
            name="John Doe",
            profile_image_url="/user.png",
            role="admin",
        )
        with mock_webui_user(id=user.id):
            response = self.fast_api_client.post(self.create_url("/api_key"))
        assert response.status_code == 200
        data = response.json()
        assert data["api_key"] is not None
        assert len(data["api_key"]) > 0

    def test_delete_api_key(self):
        user = self.auths.insert_new_auth(
            email="john.doe@openwebui.com",
            password="password",
            name="John Doe",
            profile_image_url="/user.png",
            role="admin",
        )
        self.users.update_user_api_key_by_id(user.id, "abc")
        with mock_webui_user(id=user.id):
            response = self.fast_api_client.delete(self.create_url("/api_key"))
        assert response.status_code == 200
        assert response.json() == True
        db_user = self.users.get_user_by_id(user.id)
        assert db_user.api_key is None

    def test_get_api_key(self):
        user = self.auths.insert_new_auth(
            email="john.doe@openwebui.com",
            password="password",
            name="John Doe",
            profile_image_url="/user.png",
            role="admin",
        )
        self.users.update_user_api_key_by_id(user.id, "abc")
        with mock_webui_user(id=user.id):
            response = self.fast_api_client.get(self.create_url("/api_key"))
        assert response.status_code == 200
        assert response.json() == {"api_key": "abc"}

    def test_otp_verification_invalidates_link(self):
        from open_webui.routers import auths as auths_router

        original_require = auths_router.REQUIRE_EMAIL_VERIFICATION
        original_enable_link = auths_router.ENABLE_EMAIL_VERIFICATION_LINK
        try:
            auths_router.REQUIRE_EMAIL_VERIFICATION = True
            auths_router.ENABLE_EMAIL_VERIFICATION_LINK = True

            email = "verify.otp@openwebui.com"
            user = self.auths.insert_new_auth(
                email=email,
                password=get_password_hash("password"),
                name="Verify OTP",
                profile_image_url="/user.png",
                role="pending",
            )

            otp = "123456"
            token = generate_verification_token()
            now = int(time.time())
            self._create_email_verification_record(user, otp, token, now)

            response = self.fast_api_client.post(
                self.create_url("/signup/verify"),
                json={"email": email, "otp": otp},
            )
            assert response.status_code == 200

            link_response = self.fast_api_client.get(
                self.create_url("/signup/verify/link"),
                params={"token": token, "email": email},
            )
            assert link_response.status_code == 400
        finally:
            auths_router.REQUIRE_EMAIL_VERIFICATION = original_require
            auths_router.ENABLE_EMAIL_VERIFICATION_LINK = original_enable_link

    def test_link_verification_invalidates_otp(self):
        from open_webui.routers import auths as auths_router

        original_require = auths_router.REQUIRE_EMAIL_VERIFICATION
        original_enable_link = auths_router.ENABLE_EMAIL_VERIFICATION_LINK
        try:
            auths_router.REQUIRE_EMAIL_VERIFICATION = True
            auths_router.ENABLE_EMAIL_VERIFICATION_LINK = True

            email = "verify.link@openwebui.com"
            user = self.auths.insert_new_auth(
                email=email,
                password=get_password_hash("password"),
                name="Verify Link",
                profile_image_url="/user.png",
                role="pending",
            )

            otp = "654321"
            token = generate_verification_token()
            now = int(time.time())
            self._create_email_verification_record(user, otp, token, now)

            link_response = self.fast_api_client.get(
                self.create_url("/signup/verify/link"),
                params={"token": token, "email": email},
            )
            assert link_response.status_code == 200

            response = self.fast_api_client.post(
                self.create_url("/signup/verify"),
                json={"email": email, "otp": otp},
            )
            assert response.status_code == 400
        finally:
            auths_router.REQUIRE_EMAIL_VERIFICATION = original_require
            auths_router.ENABLE_EMAIL_VERIFICATION_LINK = original_enable_link

    def test_resend_invalidates_old_tokens(self):
        from open_webui.routers import auths as auths_router

        original_require = auths_router.REQUIRE_EMAIL_VERIFICATION
        original_enable_link = auths_router.ENABLE_EMAIL_VERIFICATION_LINK
        original_send_email = auths_router.send_email
        try:
            auths_router.REQUIRE_EMAIL_VERIFICATION = True
            auths_router.ENABLE_EMAIL_VERIFICATION_LINK = True
            auths_router.send_email = lambda *args, **kwargs: None

            email = "verify.resend@openwebui.com"
            user = self.auths.insert_new_auth(
                email=email,
                password=get_password_hash("password"),
                name="Verify Resend",
                profile_image_url="/user.png",
                role="pending",
            )

            otp = "999999"
            token = generate_verification_token()
            now = int(time.time())
            self._create_email_verification_record(
                user, otp, token, now, last_sent_at=now - 3600
            )

            resend_response = self.fast_api_client.post(
                self.create_url("/signup/resend"),
                json={"email": email},
            )
            assert resend_response.status_code == 200

            otp_response = self.fast_api_client.post(
                self.create_url("/signup/verify"),
                json={"email": email, "otp": otp},
            )
            assert otp_response.status_code == 400

            link_response = self.fast_api_client.get(
                self.create_url("/signup/verify/link"),
                params={"token": token, "email": email},
            )
            assert link_response.status_code == 400
        finally:
            auths_router.REQUIRE_EMAIL_VERIFICATION = original_require
            auths_router.ENABLE_EMAIL_VERIFICATION_LINK = original_enable_link
            auths_router.send_email = original_send_email

    def test_expired_link_token_rejected(self):
        from open_webui.routers import auths as auths_router

        original_require = auths_router.REQUIRE_EMAIL_VERIFICATION
        original_enable_link = auths_router.ENABLE_EMAIL_VERIFICATION_LINK
        try:
            auths_router.REQUIRE_EMAIL_VERIFICATION = True
            auths_router.ENABLE_EMAIL_VERIFICATION_LINK = True

            email = "verify.expired@openwebui.com"
            user = self.auths.insert_new_auth(
                email=email,
                password=get_password_hash("password"),
                name="Verify Expired",
                profile_image_url="/user.png",
                role="pending",
            )

            otp = "111111"
            token = generate_verification_token()
            now = int(time.time())
            self._create_email_verification_record(
                user, otp, token, now, token_expires_at=now - 10
            )

            link_response = self.fast_api_client.get(
                self.create_url("/signup/verify/link"),
                params={"token": token, "email": email},
            )
            assert link_response.status_code == 400
        finally:
            auths_router.REQUIRE_EMAIL_VERIFICATION = original_require
            auths_router.ENABLE_EMAIL_VERIFICATION_LINK = original_enable_link
