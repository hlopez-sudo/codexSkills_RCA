---
name: managing-asset-lifecycle
description: Read existing Salesforce Revenue Cloud assets, usage and entitlements, or prepare and execute requested amendments, renewals and cancellations. Use for owned subscriptions and asset lifecycle changes. Not for new-sale quote creation, generic revenue settings or unrelated product cancellation.
---

# Managing Asset Lifecycle

Use Revenue Cloud business tools for asset lifecycle creation and ordinary line edits, SOQL for reads, and Headless Place Sales Transaction for an amendment edit that needs a QuoteAction transition. Reuse verified IDs and schemas from the current session.

For record retrieval and verification, use only connected Salesforce MCP tools. Do not use browser or Computer Use tools, inspect browser tabs, or request browser/computer permissions to retrieve records or verify record links. Once the scoped MCP read is complete, return the requested record details without extra access or URL-verification steps.

## Route by intent

| Request | Procedure |
|---|---|
| View/list account assets | Inventory below, then [raw journal entries](references/reading.md#default-raw-journal-entries). Explicit inventory-only requests skip usage. |
| Usage, balances, journals or current asset rates | [Reading assets and usage](references/reading.md) |
| Create an amendment or cancellation quote | [Amendment and cancellation](references/amend-cancel.md) |
| View or edit an existing amendment quote | [Amendment viewing and editing](references/amendment-edit.md) |
| Renew assets | [Renewal](references/renewal.md) |
| Authentication, unfamiliar schema or ambiguous response | [MCP routing](references/mcp-routing.md) |

Do not load every reference for a routine task. [Validation evidence](references/validation.md) distinguishes live tests from documentation guidance; load it when reviewing support or test coverage.

## Asset inventory

Reuse the account ID from this conversation. If missing, resolve the named account once. Query only that account:

```sql
SELECT Id, Name, Product2Id, Product2.Name, CurrentQuantity,
       LifecycleStartDate, LifecycleEndDate
FROM Asset WHERE AccountId = '<account id>' ORDER BY CreatedDate DESC
```

Present Asset.Name, current quantity and term as record details, using plain-text names by default. Include record links only when explicitly requested and the verified org URL is already available in MCP/session context; otherwise return the details without links. Do not query org domains, login history or other unrelated metadata solely to construct or verify links. Retain IDs internally for follow-up actions; never show full or shortened Asset IDs unless explicitly requested. Keep assets with identical names in separate rows. Use CurrentQuantity for the lifecycle inventory. Null Status or Quantity does not mean zero ownership or failed provisioning. Additional hierarchy, usage or financial fields are conditional on the request, not a schema preflight for this query.

After retrieving the inventory, include associated raw TransactionJournal quantities and units using [raw journal entries](references/reading.md#default-raw-journal-entries). Default to the current lifecycle term through the as-of instant and show up to five recent entries per asset with the period and preview limit disclosed; honor a requested period or all-entry view. Display only the labels, activity dates, resources, quantities and units needed to understand the entries. Do not fetch or discuss journal status, compute utilization/forecasts, or generate recommendations. Do not query entitlements, rated summaries or rates just to enrich this view.

End the asset-and-usage report with “What would you like to do next?” unless the user requested no follow-up. Do not offer action options or perform analysis to choose them. This default applies to viewing assets; it adds no usage preflight to amendment creation, line edits, conversion or activation.

When the user refers to assets just listed, reuse that selection. Follow actual hierarchy for bundles; do not discard an Anchor solely because its amount or entitlement is zero. Resolve only material ambiguity. Read-only requests authorize no asset changes.

## Required internal gate before editing an amendment

Before sending changed line or quote-side usage values, inspect the affected lines' existing QuoteAction.Type, reusing a current read-back when available.

- **No Change + an actual requested edit:** set the existing QuoteAction.Type to **Amend** before the line/child updates, in the same Headless Place Sales Transaction REST graph. Follow [amendment editing](references/amendment-edit.md). Do not first attempt a nonzero quantity through updateLines.
- **Amend:** preserve the action; batch ordinary quantity/date/price edits with updateLines when its schema supports them.
- **No effective change:** do not write or transition the action.
- **Renew, Cancel, Add or another action:** preserve it and use its own workflow.

This is a required internal prerequisite to the requested amendment, not a separate user decision. Do not narrate the QuoteAction update in commentary or final responses.

## Business inputs and scope

| Action | Tool | Shape |
|---|---|---|
| Amend | amendAssets | `{body: {assetIds, outputRecordType, amendmentStartDate, quantityChange}}` |
| Renew | renewAssets | `{body: {assetIds, outputRecordType, renewalStartDate?, renewalEndDate?}}` |
| Cancel | cancelAssets | `{body: {assetIds, outputRecordType, cancellationDate}}` |
| Edit lines | updateLines | `{salesTransactionId, changes: [{lineId, quantity?, startDate?, endDate?, ...}]}` |

Send outputRecordType explicitly. For usage amendments use Quote: Salesforce documents that direct amendment-to-Order omits required usage records. Convert the amendment quote using the Revenue Conversion skill only when requested.

Batch compatible selected assets; do not call once per asset. Use known currency, price book and asset-state-period time zone to assess compatibility. Query missing compatibility details only when needed, not as a blanket preflight for previously verified assets.

Use full ISO DateTimes. Honor an explicit effective date in the asset's stored lifecycle time zone; assets without a stored zone use UTC. The viewer's time zone does not override asset semantics. For an unspecified immediate change, use the current instant rather than an earlier local midnight. Preserve saved dates during later edits. Apply the operation-specific date rules in the relevant reference.

An amendment Quantity is a delta from StartQuantity; EndQuantity is derived. A currency Commit, a resource Grant and a seat quantity are distinct. Fetch and edit quote-side grants/rates only when the requested change needs them; use the Quote skill's usage-edit procedure. Do not edit live entitlements or shared catalog rates to change a quote.

Creating a lifecycle quote does not change the live asset. Stop at the requested boundary; use the Revenue Conversion skill for authorized conversion/activation. Never recreate a quote merely because a previous edit failed. Read persisted state before retrying an ambiguous write.

## Verify and report

Check both transport and nested business success, then read the requested values on the resulting quote. Reuse that read-back for the next request. Poll only actual pending work; do not reprice an already completed transaction or audit all grants/rates for a quantity-only edit.

When creating or viewing an amendment, show each in-scope line's **Start Quantity**, **Quantity (change)** and **End Quantity** with the quote reference. After an amendment edit, show all three saved values for each affected line, even when the edit changed a different field. Use a compact table with Asset.Name values for source assets, or meaningful line names when showing quote lines. Apply the record-details and optional-link rules in Asset inventory. Keep repeated asset names in separate rows; do not substitute IDs or ID suffixes for names. Quantity (change) is the saved amendment delta from Start Quantity, not merely the increment in the latest request; show positive/negative signs and retain zero. Do not replace these columns with only a before/after quantity summary. Use the existing scoped read-back, not an additional audit.

Keep action transitions, calculation statuses and resolved internal errors out of user-facing updates. If a requested value was not saved, identify the incomplete change plainly and distinguish saved values from requested targets.

For Monetary Commit products, report a transaction amount only when relevant to the request and verified from the currency Commit grant. Do not substitute quote totals or upfront prices, or query commitments solely to add them to a quantity-edit response. Retain exact values internally; display money/rates to two decimals.
