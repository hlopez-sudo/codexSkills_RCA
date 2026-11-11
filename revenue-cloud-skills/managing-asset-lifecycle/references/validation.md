# Validation evidence and limits

Reviewed against the repo's release 264 documentation and live calls on October 22, 2026 (America/Los_Angeles; October 23 UTC).

## Live-tested behavior

| Operation | Observed result |
|---|---|
| Asset inventory | One scoped SOQL query returned all three Pied Piper assets. CurrentQuantity was 500, 500 and 1; Quantity and Status were null. |
| Batch amendment creation | One amendAssets call with three IDs and quantityChange 0 created quote 00000042, effective January 1, 2027. API call: 15.768 seconds; first read-back: 1.242 seconds. |
| Initial calculation | The first read showed TaxCalculationWaiting; one narrow follow-up read showed CompletedWithTax. No standalone reprice was needed. |
| Nonzero delta while No Change | updateLines returned a nested business validation error despite HTTP 201. All three quantities remained unchanged. |
| Generic QuoteAction PATCH | Failed with FUNCTIONALITY_NOT_ENABLED: update is not supported for QuoteAction. Describe's updateable flag did not establish this route's support. |
| Combined REST graph | Headless Place Sales Transaction PATCHed the parent, three existing QuoteActions to Amend, then three existing lines to Quantity 500. HTTP 201, isSuccess true, empty errorResponse. Mutation call: 5.158 seconds. |
| Final read-back | Same quote/line/action/source IDs; Start 500/500/1, delta 500/500/500, End 1,000/1,000/501. January 1–October 21, 2027 dates preserved. CompletedWithPricing. |

The successful graph used pricingPref System, taxPref Skip, configurationMethod Skip and catalogRatesPref Skip. It required no Apex, second line-edit call or separate reprice. This test establishes the required No Change → Amend prerequisite and the combined REST route.

A separate immediate amendment attempt using an earlier local midnight failed the usage past-date check. Retrying with the current ISO instant succeeded. Explicit business dates must still be honored under the asset time-zone rules, not shifted automatically.

An earlier test recorded quantity-plus-commitment editing through the business Apex executor. That historical result is not evidence that every grant/rate combination has been retested through REST; the runtime instructions now use the successful REST route and do not require Apex.

## Limits

These are individual observed call durations, not a benchmark or end-to-end latency guarantee. Renewal, cancellation and downstream execution of these amendment quotes were not tested in this review. The quantity-only REST test did not audit all grants, rates or policies; platform grant proration remains possible. The source assets were not amended through order activation.

## Documentation basis

The repo's `docs/salesforce/264/dev-guide/articles/quote_and_order_capture_fields_on_quote_line_item.htm.md` defines StartQuantity as the quantity at the line's start date and EndQuantity as read-only, calculated from StartQuantity plus Quantity. The existing live read-backs returned all three fields. Displaying all three in amendment views and edit confirmations is a user-requested presentation rule; it requires no new mutation API or extra audit.

- [Asset Amendment API](https://developer.salesforce.com/docs/revenue/revenue-management/guide/connect-resources-assets-amend.html): dedicated amendment creation and Quote-first usage amendments.
- [Asset Renewal API](https://developer.salesforce.com/docs/revenue/revenue-management/guide/connect-resources-assets-renew.html): renewal inputs and optional standard dates.
- [Asset Cancellation API](https://developer.salesforce.com/docs/revenue/revenue-management/guide/connect-resources-assets-cancel.html): dedicated cancellation and required inputs.
- [Asset time-zone precision](https://help.salesforce.com/s/articleView?id=ind.qocal_asset_lifecycle_date_time_precision.htm&language=en_US&type=5): stored ASP time zone, common transaction time zone and UTC fallback.
- [Usage selling considerations](https://help.salesforce.com/s/articleView?id=ind.qocal_considerations_usage_selling.htm&language=en_US&type=5): date restrictions, expired-renewal exception and grant behavior.

The repo's postman/docs/transaction-management-apis-reference.md separates dedicated lifecycle creation from Place transaction edits and documents partial header persistence after a later processing failure. Prefer the grounded release 264 Markdown and current tool schemas over older Postman collection versions. Actual support for QuoteAction in the REST graph comes from the live test above, not an inferred generic CRUD capability.

The proposed call ordering, session reuse and conditional reads are workflow optimizations inferred from these API contracts and observed results; they are not Salesforce-mandated performance guarantees. Renewal/cancellation date behavior, nonzero delta at amendment creation and every grant/rate-edit combination have not all been exercised in this review.

## Raw usage in asset views — November 4, 2026

The connected Revenue Cloud SOQL tool returned the salesforce.com account with two assets in one account/asset relationship query. Two scoped journal queries, executed together with a five-entry limit per asset, returned two Engineering entries and three Solutions entries. Each selected ActivityDate, resource, raw Quantity and unit, bounded by that asset's lifecycle start and the as-of instant. No journal Status field, status predicate, aggregate, entitlement query, rating operation or Salesforce write was used.

The returned journal quantities were Engineering USD 58,490 and 73,400; Solutions USD 89,403, 86,943 and 42,000. These values validate direct record retrieval, not billed charges or remaining commitment. The user interrupted the asset response to request skill publication first; no completed user-facing response from that interrupted turn is claimed as a behavioral test.

The repo's release 264 TransactionJournal reference documents ReferenceRecordId, ActivityDate, UsageResourceId, Quantity, QuantityUnitOfMeasureId and UsageType. UsageCmtAssetRelatedObj documents the effective commitment relationship. The default term-to-date window, five-entry preview and neutral follow-up are workflow choices, not API requirements.

Direct association and different lifecycle start dates were live-verified. Shared-Anchor allocation, unavailable reads, all-entry pagination and other optional branches were not newly live-tested for this update. Do not add live mutations or broad tests to an ordinary asset view. Preserve all prior amendment/conversion validation limits.
