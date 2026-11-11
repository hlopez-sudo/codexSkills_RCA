---
name: managing-revenue-conversion
description: Convert Salesforce Revenue Cloud quotes into Draft orders and activate orders when requested. Supports separately requested asset provisioning. Use the Quote skill for new quote creation.
---

# Managing Revenue Conversion

For a freshly verified quote: **convert once, read the order and lines once, finish.** If activation is also requested, reuse that read-back, **activate once, verify status once**.

Use Revenue Cloud `createOrdersFromQuote`, `activateOrder` and `soqlQuery` directly. Keep dependent calls in one orchestration when possible, checking each result before continuing. Reuse the quote ID, account, currency, BillTo contact, pricing state and line details just verified in this conversation. Refresh only missing or stale information.

A quote just created here needs no repeated account, contact, product, billing, schema or existing-order lookup. No routine endpoint discovery, repricing, usage audit or asset scan.

## Convert

1. Use the intended quote with `CalculationStatus = CompletedWithPricing`, the requested lines and a non-null `BillToContactId`. If source context is missing, use the focused queries in [MCP routing](references/mcp-routing.md). Check existing orders once when conversion state is unknown; reuse an already completed stage.
2. Convert only quotes with a BillTo contact. If it is missing, stop that conversion or select another eligible quote when the user authorized that choice. Preserve commercial terms; do not change acceptance or approval status as a conversion preflight.
3. Call:

   ```json
   {"inputs":[{"quoteId":"<quote ID>"}]}
   ```

   quoteId is a plain string. Omit splitting and line-selection parameters unless requested. The default creates one order, including its lines, synchronously.
4. Check every action result's isSuccess, errors and outputValues.orderIds. If a request ID or status URL is returned, follow [async and recovery](references/mcp-routing.md). Otherwise read all returned orders and their lines once:

   ```sql
   SELECT Id,OrderNumber,Status,CalculationStatus,AccountId,QuoteId,
     CurrencyIsoCode,TotalAmount,BillToContactId,BillingCity,
     (SELECT Id,QuoteLineItemId,Product2Id,Quantity,SubscriptionTerm,
       ServiceDate,EndDate,NetUnitPrice,TotalLineAmount
      FROM OrderItems)
   FROM Order WHERE Id IN (<returned order IDs>)
   ```

   Verify Draft status, source quote/line mapping, BillTo contact, currency, product, quantity, term, dates and prices against the source. OrderItem uses ServiceDate for the start date. For a full single-order conversion, compare TotalAmount with the quote's GrandTotal. Complete pagination if present. Retain this result for activation.

Salesforce carries saved quote usage rates into order rate records during conversion. Ordinary conversion does not require reading every grant, policy, rate or adjustment before and after. Read specific usage details only for an explicitly requested preservation check or an actual discrepancy; see [extended verification](references/verification.md). Do not re-fetch Anchor catalog rates during conversion.

## Activate when requested

An eligible order is Draft, has lines and has a BillTo contact. Reuse the conversion read-back above, or query the named order once if that context is missing. An already Activated order is reported without repeating activation.

Call `activateOrder({"orderId":"<order ID>"})`. Check MCP errors and decode nested defaultExc JSON when present. Require inner isSuccess true and no business errors; HTTP 201 alone is insufficient. Then read:

```sql
SELECT Id,OrderNumber,Status,ActivatedDate,CalculationStatus,
  BillToContactId,QuoteId,TotalAmount,CurrencyIsoCode
FROM Order WHERE Id IN (<activated order IDs>)
```

Confirm Status = Activated and ActivatedDate. A conversion-only request ends with the Draft order. A request through activation ends with verified activation. Continue authorized stages without asking permission again.

## Conditional paths

- New quote requested: use the installed Quote skill and reuse its verified result here.
- Split/partial orders, pending processing, errors or ambiguous writes: read [MCP routing and recovery](references/mcp-routing.md). Verify every returned order and resume only missing work.
- Asset creation/provisioning requested: read [verification and provisioning](references/verification.md). Activation alone does not prove provisioning. Do not add asset queries or orderToAsset to an activation-only request.

## Report

Return quote/order links, actual status and a brief confirmation of requested quantity and term. Include totals when relevant. Keep priced charges, monetary commitments and allowances distinct. Do not infer commitment size from an order total or claim specific negotiated terms were preserved without verification.

[Validation evidence](references/validation.md) is for maintenance, not required reading during execution.
