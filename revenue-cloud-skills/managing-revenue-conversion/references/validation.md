# Validation evidence and limits

Maintenance reference; not a runtime preflight.

## Live test: October 22, 2026, America/Los_Angeles

Org: trailsignup-22f202b7c11721.my.salesforce.com.

The user authorized fresh quote creation through activation. The Quote skill's Headless Place route created Pied Piper Quote 00000039 (0Q0bm000003qh0jCAA) with 500 GPT Enterprise Monetary Commit users, SubscriptionTerm 1, October 22, 2026–October 21, 2027, Annual billing, Billing Treatment - USA - Advance, and the account's first contact as BillTo.

Quote read-back confirmed Draft, CompletedWithPricing, BillTo and the requested line/billing fields. Revenue Cloud createOrdersFromQuote accepted a plain-string quote ID in an inputs array and returned Draft Order 00000105 (801bm000039vgS2AAI) without an async tracker.

One Order query with OrderItems verified source quote/line IDs, BillTo, product, quantity, SubscriptionTerm, ServiceDate/EndDate, NetUnitPrice and line/header totals. activateOrder returned nested isSuccess true with no errors. Final read-back confirmed Activated and ActivatedDate.

| Calls | Milliseconds |
|---|---:|
| Headless quote create | 5,535 |
| Quote verification | 1,161 |
| Revenue Cloud conversion | 9,522 |
| Order and lines verification | 1,193 |
| Revenue Cloud activation | 8,343 |
| Activated status verification | 1,214 |
| Six-call total | 26,968 |

The timed sequence took 72,762 ms wall-clock including orchestration. A prior account/contact lookup took 1,861 ms and is outside that sequence; earlier discovery/preparation is also excluded. This is not evidence of a sub-30-second complete assistant turn.

Conversion plus verification took 10,715 ms; activation plus verification took 9,557 ms. No retry, reprice, usage audit or asset query was needed. Direct Headless dispatch successfully executed Place despite earlier unrelated discovery results.

## Proven and untested

Proven: a priced Draft quote with BillTo converted without acceptance/approval changes in this org; single-order creation included its line synchronously; the tested commercial fields carried through; activation succeeded and persisted. Reusing the order read-back avoided another activation preflight.

Both quote and order had USD 0 in priced charges. This does not establish commitment size or prove nonzero discount arithmetic.

This run did not compare every usage grant, policy or rate adjustment, or test asset provisioning, automatic asset creation, split/partial orders, ramped/lifecycle orders, async recovery or INVALID_OPERATION repricing recovery. Conditional guidance for these paths comes from documented contracts and existing safeguards.

Evidence: conversion-optimization-review/e2e-quote39-order105.json in the review workspace.

## Canonical documentation

- [Create Orders From Quote](https://developer.salesforce.com/docs/revenue/revenue-management/guide/actions-obj-create-orders-from-quote.html): input/output contract; synchronous single-order versus asynchronous split-line behavior.
- [Saving Usage Rates for Quotes and Orders](https://help.salesforce.com/s/articleView?id=ind.qocal_saving_usage_rates_for_quotes_and_orders.htm&language=en_US&type=5): saved quote rates transform into order rate records.
- [Multiple-order considerations](https://help.salesforce.com/s/articleView?id=ind.qocal_split_quote_to_orders_important_considerations.htm&language=en_US&type=5): pricing preservation and risk of reapplying header adjustments.

Repository release-264 snapshots:
- docs/salesforce/264/dev-guide/articles/actions_obj_create_orders_from_quote.htm.md
- docs/salesforce/264/help/articles/ind.qocal_saving_usage_rates_for_quotes_and_orders.htm.md
- docs/salesforce/264/help/articles/ind.qocal_split_quote_to_orders_important_considerations.htm.md
