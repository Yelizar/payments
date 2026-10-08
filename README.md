# payment

Сервис приёма платежей. API только принимает запрос и кладёт его в БД, дальше уже воркеры:

1. пишем платёж и outbox событие в одной транзакции
2. outbox публикует в Rabbit
3. consumer эмулирует платеж и дергает webhook

## Запуск

```bash
cp .env.example .env
docker compose up --build
```

```bash
curl -X POST http://localhost:8000/api/v1/payments \
  -H 'X-API-Key: test-api-key' \
  -H 'Idempotency-Key: order-123' \
  -H 'Content-Type: application/json' \
  -d '{"amount": "100.00", "currency": "RUB", "webhook_url": "http://host.docker.internal:9000/webhook"}'
```

Статус потом так:

```bash
curl http://localhost:8000/api/v1/payments/<id> -H 'X-API-Key: test-api-key'
```

## Очереди

`payments.new` - основная, `payments.retry` - отложенный повтор через TTL сообщения, после третьей ошибки уходит в `payments.dlq`.