import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from typing import Any


class TotvsModaError(RuntimeError):
    pass


def _env_int(name: str, default: int | None = None) -> int | None:
    value = os.getenv(name)
    if value in (None, ""):
        return default
    return int(value)


def _env_float(name: str, default: float = 0.0) -> float:
    value = os.getenv(name)
    if value in (None, ""):
        return default
    return float(value)


def totvs_settings() -> dict[str, Any]:
    return {
        "token_url": os.getenv("TOTVS_TOKEN_URL", ""),
        "order_url": os.getenv("TOTVS_ORDER_URL", ""),
        "client_id": os.getenv("TOTVS_CLIENT_ID", ""),
        "client_secret": os.getenv("TOTVS_CLIENT_SECRET", ""),
        "grant_type": os.getenv("TOTVS_GRANT_TYPE", "password"),
        "username": os.getenv("TOTVS_USERNAME", ""),
        "password": os.getenv("TOTVS_PASSWORD", ""),
        "order_id_prefix": os.getenv("TOTVS_ORDER_ID_PREFIX", "TRANSF-"),
        "branch_code": _env_int("TOTVS_BRANCH_CODE"),
        "operation_code": _env_int("TOTVS_OPERATION_CODE"),
        "customer_code": _env_int("TOTVS_CUSTOMER_CODE"),
        "customer_cpf_cnpj": os.getenv("TOTVS_CUSTOMER_CPF_CNPJ", ""),
        "representative_code": _env_int("TOTVS_REPRESENTATIVE_CODE", 32098),
        "representative_cpf_cnpj": os.getenv("TOTVS_REPRESENTATIVE_CPF_CNPJ", ""),
        "payment_condition_code": _env_int("TOTVS_PAYMENT_CONDITION_CODE", 1),
        "priority_code": _env_int("TOTVS_PRIORITY_CODE", 1),
        "status_order": _env_int("TOTVS_STATUS_ORDER", 1),
        "batch_order": os.getenv("TOTVS_BATCH_ORDER", ""),
        "item_price": _env_float("TOTVS_ORDER_ITEM_PRICE_DEFAULT", 0.0),
        "shipping_company_code": _env_int("TOTVS_SHIPPING_COMPANY_CODE"),
        "freight_type": os.getenv("TOTVS_FREIGHT_TYPE", ""),
    }


def missing_totvs_settings(settings: dict[str, Any]) -> list[str]:
    required = [
        "token_url",
        "order_url",
        "client_id",
        "client_secret",
        "grant_type",
        "username",
        "password",
        "branch_code",
        "payment_condition_code",
        "priority_code",
        "status_order",
    ]
    missing = [name for name in required if settings.get(name) in (None, "")]
    if not settings.get("representative_code") and not settings.get("representative_cpf_cnpj"):
        missing.append("representative_code ou representative_cpf_cnpj")
    return missing


def _row_float(row: dict[str, Any], key: str, default: float = 0.0) -> float:
    value = row.get(key)
    if value in (None, ""):
        return default
    return float(value)


def _row_int(row: dict[str, Any], key: str) -> int | None:
    value = row.get(key)
    if value in (None, ""):
        return None
    return int(value)


def _coverage(stock: float, monthly_average: float) -> float:
    if monthly_average <= 0:
        return 0.0
    return round(stock / monthly_average, 2)


def get_operation_code_for_loja(cd_loja: int) -> int:
    """Retorna o operation_code baseado na loja (conforme regra BI LIEBE)."""
    if cd_loja in (2, 3, 4, 5, 6, 7, 8, 19, 21, 22):
        return 598
    if cd_loja in (10, 14, 15, 20, 120):
        return 30
    if cd_loja == 17:
        return 310
    return 598  # default


def get_customer_code_for_loja(cd_loja: int) -> int:
    """Retorna o customer_code (cd_pessoa) baseado na loja."""
    return 110000000 + cd_loja


def build_order_payload(
    *,
    order_id: str,
    order_date: datetime,
    rows: list[dict[str, Any]],
    settings: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cfg = settings or totvs_settings()
    valid_rows = [row for row in rows if float(row.get("qtd_pedido") or 0) > 0]
    first_row = valid_rows[0] if valid_rows else {}

    # Calcular preço usando preco_fabrica ou price
    def get_price(row: dict[str, Any]) -> float:
        return _row_float(row, "preco_fabrica", _row_float(row, "price", cfg["item_price"]))

    total_amount = round(
        sum(float(row.get("qtd_pedido") or 0) * get_price(row) for row in valid_rows),
        2,
    )

    # Obter cd_loja para calcular operation_code e customer_code
    cd_loja = _row_int(first_row, "cd_loja") or 0

    # Operation code: primeiro tenta da row, depois calcula pela loja, depois default
    operation_code = _row_int(first_row, "operation_code")
    if not operation_code and cd_loja:
        operation_code = get_operation_code_for_loja(cd_loja)
    if not operation_code:
        operation_code = cfg.get("operation_code")

    # Customer code: primeiro tenta da row, depois calcula (cd_pessoa = 110000000 + cd_loja)
    customer_code = _row_int(first_row, "customer_code")
    if not customer_code and cd_loja:
        customer_code = get_customer_code_for_loja(cd_loja)
    if not customer_code:
        customer_code = cfg.get("customer_code")

    payment_condition_code = _row_int(first_row, "payment_condition_code") or cfg["payment_condition_code"]
    shipping_company_code = _row_int(first_row, "shipping_company_code") or cfg["shipping_company_code"]
    freight_type = first_row.get("freight_type") or cfg["freight_type"]
    payload: dict[str, Any] = {
        "orderId": order_id,
        "branchCode": cfg["branch_code"],
        "orderDate": order_date.isoformat(),
        "operationCode": operation_code,
        "paymentConditionCode": payment_condition_code,
        "priorityCode": cfg["priority_code"],
        "statusOrder": cfg["status_order"],
        "batchOrder": cfg["batch_order"],
        "totalAmountOrder": total_amount,
        "items": [
            {
                "productCode": int(row["cd_produto"]),
                "reference": str(row.get("referencia") or ""),
                "color": str(row.get("cor") or ""),
                "size": str(row.get("tamanho") or ""),
                "quantity": float(row["qtd_pedido"]),
                "originalPrice": get_price(row),
                "price": get_price(row),
                "discountPercentage": _row_float(row, "discount_percentage", 0.0),
                "discountValue": _row_float(row, "discount_value", 0.0),
                "currentCoverage": _coverage(
                    _row_float(row, "saldo_inicial"),
                    _row_float(row, "media_mensal"),
                ),
                "projectedCoverage": _coverage(
                    _row_float(row, "saldo_inicial")
                    + _row_float(row, "qtd_ja_programada")
                    + _row_float(row, "qtd_pedido"),
                    _row_float(row, "media_mensal"),
                ),
                "calculationMemory": {
                    "mediaMensal": _row_float(row, "media_mensal"),
                    "saldoInicial": _row_float(row, "saldo_inicial"),
                    "entradaTotal": _row_float(row, "entrada_total"),
                    "necessidade": _row_float(row, "necessidade"),
                    "faltaBruta": _row_float(row, "qtd_sugerida_bruta", _row_float(row, "qtd_sugerida")),
                    "pendentePedido": _row_float(row, "qtd_pendente_pedido"),
                    "transito": _row_float(row, "qtd_transito"),
                    "jaProgramado": _row_float(row, "qtd_ja_programada"),
                    "pedidoFinal": _row_float(row, "qtd_pedido"),
                },
            }
            for row in valid_rows
        ],
        "observations": [
            {
                "observation": "Pedido gerado pelo processo de reposicao LIEBE."
            }
        ],
    }
    if customer_code:
        payload["customerCode"] = customer_code
    elif cfg.get("customer_cpf_cnpj"):
        payload["customerCpfCnpj"] = cfg["customer_cpf_cnpj"]
    if shipping_company_code:
        payload["shippingCompanyCode"] = shipping_company_code
    if freight_type:
        payload["freightType"] = freight_type
    if cfg.get("representative_code"):
        payload["representativeCode"] = cfg["representative_code"]
    elif cfg.get("representative_cpf_cnpj"):
        payload["representativeCpfCnpj"] = cfg["representative_cpf_cnpj"]
    return {key: value for key, value in payload.items() if value not in (None, "")}


class TotvsModaClient:
    def __init__(self, settings: dict[str, Any] | None = None):
        self.settings = settings or totvs_settings()

    def get_token(self) -> str:
        body = urllib.parse.urlencode(
            {
                "client_id": self.settings["client_id"],
                "client_secret": self.settings["client_secret"],
                "grant_type": self.settings["grant_type"],
                "username": self.settings["username"],
                "password": self.settings["password"],
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            self.settings["token_url"],
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise TotvsModaError(exc.read().decode("utf-8", errors="ignore")) from exc
        except urllib.error.URLError as exc:
            raise TotvsModaError(str(exc)) from exc
        token = data.get("access_token") or data.get("token")
        if not token:
            raise TotvsModaError("Token TOTVS nao retornou access_token.")
        return token

    def create_order(self, payload: dict[str, Any]) -> dict[str, Any]:
        token = self.get_token()
        request = urllib.request.Request(
            self.settings["order_url"],
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise TotvsModaError(exc.read().decode("utf-8", errors="ignore")) from exc
        except urllib.error.URLError as exc:
            raise TotvsModaError(str(exc)) from exc
