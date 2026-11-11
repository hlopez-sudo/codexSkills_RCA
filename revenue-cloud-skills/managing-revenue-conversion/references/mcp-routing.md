# MCP routing and recovery

Read this for missing source context, requested split/partial orders, actual errors or a demonstrated tool gap. Basic conversion and activation are self-contained in SKILL.md.

## Focused source queries

Use Revenue Cloud soqlQuery with escaped literal values; it does not bind Apex-style variables. Raw spaces work in q.

If the intended quote has not just been verified:

```sql
SELECT Id,QuoteNumber,QuoteAccountId,Status,CalculationStatus,
  CurrencyIsoCode,GrandTotal,BillToContactId,
  (SELECT Id,Product2Id,Quantity,SubscriptionTerm,StartDate,EndDate,
    NetUnitPrice,NetTotalPrice FROM QuoteLineItems)
FROM Quote WHERE Id='<quote ID>'
```

When conversion state is unknown:

```sql
SELECT Id,OrderNumber,Status,QuoteId
FROM Order WHERE QuoteId='<quote ID>'
```

These queries can run in parallel. Skip the duplicate check for a quote just created here with no conversion attempt. If orders exist, reuse the completed conversion; inspect source-line coverage before creating any separately requested additional partial order. An ambiguous previous attempt always requires a persisted-state check.

Reuse verified fields, schemas and connection context. No routine identity, metadata or feature-toggle preflight. After reconnecting or changing target org, confirm the intended record in that connection before writing. Resolve a missing BillTo through a separately authorized quote edit; do not convert first and attempt generic Order PATCH repairs.

## Parse results and handle actual async work

Prefer structuredContent; otherwise parse text JSON. Check MCP isError and every business result. Invocable arrays may be inside a structured content wrapper. Inspect every result's isSuccess, errors and outputValues.

Activation can return defaultExc as a JSON string even on success. Decode it and check the business result.

CreateSingleOrder creates headers and lines synchronously. Do not insert sleeps or poll a tracker when no async operation was returned. If quote pricing is actually pending, poll only its calculation state with bounded backoff; a terminal failure requires error handling.

For requested CreateOrderByGroup or CreateOrderByField, headers are synchronous and lines asynchronous. Use the current tool contract for requested parameters and quoteLineItemIds for requested line selection. Preserve all order IDs. Follow returned requestId and statusUrl (or statusURL) through the documented tracker and verify line completion before activation.

Poll known pending work with modest backoff and a bounded wait, normally up to two minutes. Report any remaining pending state and identifier rather than resubmitting. For partial/split orders, compare each order with its selected source lines rather than the full quote total.

## Errors and retries

After a timeout, business error or partial create, inspect returned IDs and persisted source-linked orders before retrying. Resume only missing work.

On INVALID_OPERATION, inspect the actual reason and pricing state. If calculation is pending, wait. Do not treat every INVALID_OPERATION as a pricing problem. Use repriceSalesTransaction only under its explicit repricing contract and the user's authorization. After an authorized reprice completes, retry conversion at most once after confirming no orders were created.

Do not routinely reprice orders created from quotes. Salesforce documents that repricing can reapply carried header adjustments and over-discount the order.

For an activation error, inspect its nested business error and current order status. Do not repeat a successful activation or patch Order.Status to bypass the business action.

## Headless only for a gap

Use Headless for needed reads, metadata or business actions that Revenue Cloud tools cannot express. Follow its discovery/description contract for an unfamiliar operation; reuse a compatible operation already resolved in the session. Rephrase unrelated discovery once, then report a capability gap rather than cycling through Commerce or Industries CPQ workflows.

Keep credentials in the connection store. Authentication failure requires supported reauthentication, not repeated discovery or a transport switch. Inspect both status_code and body in Headless responses.

New quotes belong to the installed Quote skill and its Place Sales Transaction route, including billing fields and BillTo contact. Do not substitute createSalesTransaction/addLines for that creation workflow.
