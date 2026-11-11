# MCP routing and response contract

## Reuse the supported path

Use current Revenue Cloud business tools for amend/renew/cancel creation and supported line edits, and soqlQuery for reads. Use Headless Place Sales Transaction when the requested amendment needs its QuoteAction changed. Do not call both connectors for every task.

Reuse verified account/asset/quote IDs, tool schemas, source mappings and described operations within the session. Skip routine identity, schema, discovery and describe calls when that context is established. Refresh only what is stale, missing, affected by a connection switch or contradicted by an actual error. Current quantities and commercial terms are not permanent cache entries.

Use scoped SOQL and escape real values; the connector does not bind Apex-style variables. Check child-query pagination as well as top-level pagination. Batch independent reads when needed, inspect every result and chunk large ID lists to fit the actual request limits.

## Headless

Reuse the known compatible Place operation in [amendment editing](amendment-edit.md). For a new unsupported operation or genuine adapter gap, discover/describe the matching Revenue Management operation once and copy its method, path and schema. Do not substitute Commerce, Industries CPQ or shared catalog APIs. Do not guess wrapper shapes repeatedly.

Use dispatch_readonly for reads and dispatch for writes. Keep query parameters separate. Use the verified operation's API version; a version in a record URL does not establish another route. Do not use direct QuoteAction sObject PATCH, Apex or direct entitlement DML as an alternative to the verified transaction graph.

Before moving record IDs to a connector whose org context is not established, confirm the same unique org-bound target through it. A fresh matching target read is sufficient; do not add a full identity audit. After reauthentication, refresh the affected target before retrying an ambiguous mutation.

## Parse business results

Check MCP isError and plain text errors before parsing. Prefer structuredContent, otherwise parse JSON text when present; OAuth errors may not be JSON. Revenue Cloud can embed a JSON string in defaultExc even on successful calls. Decode it and inspect nested isSuccess/success, errors and returned IDs. HTTP 201 or isError false alone does not establish business success. Inspect every result in invocable-action arrays.

Headless returns status_code and body. Check both transport and body business results.

A requestId alone is not evidence of pending work. On success with a record ID and no pending status, read the result directly. If the response or read-back says processing is pending, use a supplied tracker/statusUrl or a narrow header poll with modest bounded backoff. Follow actual terminal/error states. Do not wait for CompletedWithPricing when the transaction is already CompletedWithTax.

## Recovery and authorization

After a timeout, ambiguous error or partial create, read persisted state before retrying. A header can survive later failure. Repair missing requested work without recreating the quote or replaying an additive change twice. A client-side schema rejection before execution differs from an uncertain server outcome.

If authentication fails, identify the affected connection and use supported reauthentication. Do not loop doomed calls, extract credentials or substitute raw authenticated HTTP. Read-only skill review can continue without a live connection.

Preparing a quote does not authorize activation, approval, provisioning, shared-catalog edits or live entitlement repair. Continue the stages the user requested and report any incomplete requested change accurately.
