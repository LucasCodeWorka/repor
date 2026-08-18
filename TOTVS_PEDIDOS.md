# Integracao TOTVS Moda - Pedidos de Reposicao

## Endpoints mapeados

- Token: `TOTVS_TOKEN_URL`
- Pedido: `TOTVS_ORDER_URL`
- Swagger: `/api/totvsmoda/sales-order/v2/swagger/v1/swagger.json`
- Inclusao de pedido: `POST /api/totvsmoda/sales-order/v2/b2c-orders`

## Variaveis de ambiente

Nao gravar credenciais em codigo. Configurar no ambiente local:

```env
TOTVS_TOKEN_URL=
TOTVS_ORDER_URL=
TOTVS_CLIENT_ID=
TOTVS_CLIENT_SECRET=
TOTVS_GRANT_TYPE=password
TOTVS_USERNAME=
TOTVS_PASSWORD=

TOTVS_ORDER_ID_PREFIX=TRANSF-
TOTVS_BRANCH_CODE=
TOTVS_REPRESENTATIVE_CODE=32098
TOTVS_REPRESENTATIVE_CPF_CNPJ=
TOTVS_PAYMENT_CONDITION_CODE=1
TOTVS_PRIORITY_CODE=1
TOTVS_STATUS_ORDER=1
TOTVS_BATCH_ORDER=
TOTVS_ORDER_ITEM_PRICE_DEFAULT=0
TOTVS_SHIPPING_COMPANY_CODE=
TOTVS_FREIGHT_TYPE=
```

## Rotas internas criadas

- `GET /api/totvs/config-status`
- `POST /api/processo-reposicao/pedido-totvs/preview`
- `POST /api/processo-reposicao/pedido-totvs/enviar`

O envio real exige `confirmar=true` e configuracao completa.

## Tipos de pedido

- `CURVA_A_AA`
- `CURVA_BC_1`
- `CURVA_BC_2`

## De-para do pedido

- `productCode`: `dPRODUTO.idproduto`
- `quantity`: quantidade calculada pelo processo de reposicao
- `customerCode`: `dEMPRESA.cd_pessoa`, com um pedido separado por loja
- `originalPrice`: `dPRODUTO.prcpfabrica`
- `price`: `dPRODUTO.prcpfabrica`
- `discountPercentage`: `0`
- `discountValue`: `0`
- `operationCode`: `598` para empresas `2,3,4,5,6,7,8,19,21,22`; `30` para `10,14,15,20,120`; `310` para `17`
- `paymentConditionCode`: `1`
- `shippingCompanyCode`: vazio, exceto se `TOTVS_SHIPPING_COMPANY_CODE` for configurado
- `freightType`: vazio, exceto se `TOTVS_FREIGHT_TYPE` for configurado

## Pendencias de regra

- `TOTVS_BRANCH_CODE`: empresa emissora do pedido.
- Confirmar se a API aceita `quantity` decimal ou se devemos arredondar todas as quantidades.
- Confirmar se `shippingCompanyCode` e `freightType` podem ficar vazios no pedido real.
