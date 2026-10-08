PAYMENTS_NEW_QUEUE = "payments.new"
PAYMENTS_RETRY_QUEUE = "payments.retry"
PAYMENTS_DLQ = "payments.dlq"
PAYMENTS_EXCHANGE = "payments"
PAYMENTS_DLX = "payments.dlx"
MAX_PROCESS_ATTEMPTS = 3
# 1с после первой ошибки, 2с после второй; третья сразу в DLQ
RETRY_DELAYS_SECONDS = (1, 2)


def retry_delay_seconds(failed_attempt: int) -> int:
    return RETRY_DELAYS_SECONDS[failed_attempt - 1]
