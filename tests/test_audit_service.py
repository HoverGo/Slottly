from starlette.requests import Request

from app.services.audit_service import (
    infer_company_id,
    redact_details,
    should_audit_request,
)


def _request(method: str, path: str) -> Request:
    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "headers": [],
        "client": ("127.0.0.1", 12345),
        "server": ("test", 80),
        "scheme": "http",
        "query_string": b"",
        "root_path": "",
    }
    return Request(scope)


def test_redact_details_masks_passwords():
    data = {"email": "a@b.c", "password": "secret", "nested": {"token": "x"}}
    redacted = redact_details(data)
    assert redacted["email"] == "a@b.c"
    assert redacted["password"] == "***"
    assert redacted["nested"]["token"] == "***"


def test_should_audit_admin_get():
    request = _request("GET", "/api/v1/admin/dashboard")
    assert should_audit_request(request) is True


def test_should_audit_skip_login():
    request = _request("POST", "/api/v1/auth/login")
    assert should_audit_request(request) is False


def test_should_audit_company_mutation():
    request = _request("PATCH", "/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/services/1")
    assert should_audit_request(request) is True


def test_infer_company_id_from_path():
    company_id = infer_company_id("/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/members")
    assert str(company_id) == "550e8400-e29b-41d4-a716-446655440000"
