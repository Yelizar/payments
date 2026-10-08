from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    status,
)

from app.container import container
from app.core.application.services.payment import (
    PaymentNotFoundException,
    PaymentService,
    PaymentServiceException,
)
from app.core.presentation.schemas import (
    CreatePaymentRequest,
    CreatePaymentResponse,
    PaymentDetailResponse,
)

payments_router = APIRouter()


@payments_router.post(
    "/payments",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=CreatePaymentResponse,
)
async def create_payment(
    request: CreatePaymentRequest,
    idempotency_key: Annotated[str, Header()],
    payment_service: PaymentService = Depends(container.get_payment_service),
) -> CreatePaymentResponse:
    try:
        return await payment_service.create_payment(request, idempotency_key)
    except PaymentServiceException as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@payments_router.get(
    "/payments/{payment_id}",
    response_model=PaymentDetailResponse,
    status_code=status.HTTP_200_OK,
)
async def get_payment(
    payment_id: UUID,
    payment_service: PaymentService = Depends(container.get_payment_service),
) -> PaymentDetailResponse:
    try:
        return await payment_service.get_payment(payment_id)
    except PaymentNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
