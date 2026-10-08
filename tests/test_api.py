from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api import get_app
from app.container import container
from app.core.application.services.payment import PaymentNotFoundException
from app.core.domain.enums import Currency, PaymentStatus
from app.core.presentation.schemas import CreatePaymentResponse, PaymentDetailResponse


API_KEY = "test-api-key"


def test_create_payment_requires_api_key():
    client = TestClient(get_app())

    response = client.post(
        "/api/v1/payments",
        json={"amount": "10.00", "currency": "RUB"},
        headers={"Idempotency-Key": "order-1"},
    )

    assert response.status_code == 401


def test_create_payment_delegates_to_service():
    service = AsyncMock()
    expected = CreatePaymentResponse(
        payment_id=uuid4(),
        status=PaymentStatus.PENDING,
        created_at=datetime.now(UTC),
    )
    service.create_payment.return_value = expected
    app = get_app()
    app.dependency_overrides[container.get_payment_service] = lambda: service

    try:
        response = TestClient(app).post(
            "/api/v1/payments",
            json={"amount": "10.00", "currency": "RUB"},
            headers={"X-API-Key": API_KEY, "Idempotency-Key": "order-1"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 202
    assert response.json()["payment_id"] == str(expected.payment_id)
    service.create_payment.assert_awaited_once()


def test_get_payment_maps_not_found_to_404():
    service = AsyncMock()
    payment_id = uuid4()
    service.get_payment.side_effect = PaymentNotFoundException(
        f"Payment not found: {payment_id}"
    )
    app = get_app()
    app.dependency_overrides[container.get_payment_service] = lambda: service

    try:
        response = TestClient(app).get(
            f"/api/v1/payments/{payment_id}",
            headers={"X-API-Key": API_KEY},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["detail"] == f"Payment not found: {payment_id}"


def test_get_payment_returns_service_response():
    service = AsyncMock()
    payment_id = uuid4()
    expected = PaymentDetailResponse(
        payment_id=payment_id,
        amount=Decimal("10.00"),
        currency=Currency.RUB,
        status=PaymentStatus.SUCCEEDED,
        created_at=datetime.now(UTC),
    )
    service.get_payment.return_value = expected
    app = get_app()
    app.dependency_overrides[container.get_payment_service] = lambda: service

    try:
        response = TestClient(app).get(
            f"/api/v1/payments/{payment_id}",
            headers={"X-API-Key": API_KEY},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["status"] == PaymentStatus.SUCCEEDED.value
    assert response.json()["amount"] == "10.00"

