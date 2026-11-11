# Read asset inventory and usage

For account asset views, use the inventory query in [SKILL.md](../SKILL.md), then follow **Default: raw journal entries** below. An explicit inventory-only request skips usage. Reuse resolved account/asset IDs and verified schema; do not add routine metadata, entitlement or rate discovery.

## Default: raw journal entries

1. Use the requested period, or each asset's current lifecycle term through the query's as-of instant. Filter on ActivityDate using full ISO DateTimes and disclose the period. Exclude future activity. If the asset has not started, its term has ended, or the term cannot be established, state that briefly rather than choosing an invented current window.
2. Read directly associated journals through ReferenceRecordId with UsageType = UsageManagement. Reuse known Anchor/binding mappings where applicable. When a Commit/Pack has no direct journals and its attribution is unresolved, query only the relevant relationship needed to locate its usage. A shared account or product name does not prove attribution. UsageCmtAssetRelatedObj supplies the commitment asset, related object and effective window; account/contract bindings may need a narrower asset/resource mapping. Show shared Anchor entries once and identify the association, without allocating the same entries to multiple commitments.
3. Return up to five latest entries per asset by default, preserving the saved Quantity, sign, resource and unit. Disclose the limit; retrieve all pages only when all entries are requested. Batch compatible reads and run independent bounded queries together when per-asset limits require separate queries. Use verified child relationships if available; do not rediscover them for each request.
4. Do not query, filter, group, analyze or report journal Status for this raw-entry view. Do not query grants, balances, rating jobs or catalog rates, compute totals/percentages/forecasts, or generate recommendations. These records are raw journal quantities, not proof of billed charges or commitment drawdown.
5. Distinguish no matching entries from an unavailable query or unresolved attribution. Preserve nulls rather than converting them to zero. Do not silently omit an asset when its usage read fails; return the available inventory and identify the missing usage briefly.

The following bounded query succeeded through the connected Revenue Cloud SOQL tool. Substitute the selected asset and reporting bounds:

```sql
SELECT Id, Name, ReferenceRecordId, ActivityDate,
       UsageResourceId, UsageResource.Name, Quantity,
       QuantityUnitOfMeasureId, QuantityUnitOfMeasure.Name
FROM TransactionJournal
WHERE ReferenceRecordId = '<asset id>'
  AND UsageType = 'UsageManagement'
  AND ActivityDate >= <period start ISO DateTime>
  AND ActivityDate <= <as-of ISO DateTime>
ORDER BY ActivityDate DESC, Id DESC
LIMIT 5
```

For a combined query, use resolved IDs and per-asset bounds where terms differ. A single global LIMIT must not silently remove another asset's entries. Counts returned by a limited query describe the returned rows, not necessarily every matching entry; do not add a count query just for presentation.

Present the asset inventory, then `Asset | Activity date | Resource | Quantity | Unit`. Use compact per-asset sections when clearer. Apply the asset-name, internal-ID and optional-link rules from SKILL.md. Keep different resources and units separate, including currency versus tokens. A USD journal quantity is a recorded usage amount, not the asset's commitment. Display money to two decimals without deriving new amounts.

Include no status columns, counts, labels or commentary, and no recommendations or suggested action menu. Finish with exactly:

> What would you like to do next?

Honor an explicit request to omit follow-up questions. Asset viewing is read-only: do not ingest usage, run orchestration/rating, repair records or start an amendment. Stop after reporting; the sections below apply only when the user separately requests deeper information.

## Explicit requests for balances, rates or analysis

Do not assume Asset has ContractId. Resolve contract/order/asset relationships through verified fields. Keep nulls distinct from zeros, and do not assume a commitment asset always has a zero price.

## Usage questions need a period and attribution

Select the requested as-of date or term. State the reporting period. Read entitlements with identity, resource/unit IDs and effective start/end fields so multiple historical/future rows can be distinguished:

```sql
SELECT Id, AssetId, UsageResourceId, UsageResource.Name,
       UsageResource.Category, EntitlementUomId, EntitlementUom.Name,
       GrantType, EntitlementQuantity, ActionType,
       EffectiveStartDateTime, EffectiveEndDateTime
FROM TransactionUsageEntitlement WHERE AssetId IN (<resolved ids>)
```

These entitlement field names came from the source and need live metadata validation. Do not put non-aggregate aliases on a normal SOQL field list.

Choose the applicable entitlement for the asset/resource/unit/grant type and reporting period, using verified validity and supersession rules. Latest CreatedDate or latest non-Renewal row alone is not sufficient: it might be future dated, cancelled, outside the current term or superseded. Never sum all historical Commit rows. If multiple overlapping rows remain ambiguous, show them with their dates and withhold a single balance.

Aggregate journals for the **same period and attribution scope**, with explicit aliases for potentially duplicate Name fields:

```sql
SELECT ReferenceRecordId, UsageResourceId,
       UsageResource.Name resourceName,
       UsageResource.Category resourceCategory,
       QuantityUnitOfMeasureId,
       QuantityUnitOfMeasure.Name unitName,
       SUM(Quantity) consumed, COUNT(Id) journalCount,
       MIN(ActivityDate) firstUsage, MAX(ActivityDate) lastUsage
FROM TransactionJournal
WHERE ReferenceRecordId IN (<resolved attribution ids>)
  AND UsageType = 'UsageManagement'
  AND ActivityDate >= <period start>
  AND ActivityDate < <exclusive period end>
GROUP BY ReferenceRecordId, UsageResourceId, UsageResource.Name,
         UsageResource.Category, QuantityUnitOfMeasureId,
         QuantityUnitOfMeasure.Name
```

Use the actual ActivityDate field type when forming date literals. Validate journal status/reversal semantics and filter or net them according to the org's model; do not call every recorded row billable consumption without evidence. Aggregate pagination/row limits must be handled or the totals are incomplete. A failed query is not zero consumption.

## Remaining amount

`remaining = applicable granted amount - consumed in that entitlement's period` only when resource identity, unit, denomination and subscription/wallet attribution match. `NetQuantity` and `TransactionQuantity` are not assumed remaining-balance fields. Do not subtract lifetime usage from a current-term commitment, sum unrelated wallets or convert tokens to USD with an invented rate.

Usage may be recorded against a related Anchor asset. Establish that relationship from actual transaction/binding records before allocating its journals to a commitment. Reading all account assets can find candidates, but sharing an account or product name is not proof of a shared wallet. If attribution cannot be established, show consumption and commitment separately and mark remaining unavailable.

Keep Currency, Token and Usage categories and input/output units separate. A Currency resource's Quantity can represent money; confirm its denomination. Zero-valued allowances may be summarized with their count and units if no consumption is hidden. Nonzero or consumed rows remain visible.

## Rate/policy details and history

Use a matching Revenue Cloud read tool if exposed. Otherwise discover/describe a compatible Headless asset usage-detail operation. The source suggested `/services/data/v{version}/asset-management/assets/{assetId}/usage-details` with required effectiveDate; this is a lookup hint, not a dispatch-ready route. Copy the actual described path and required parameters, and inspect only the named assets. Do not use the quote's pricing as the live asset's pricing.

For an explicit request for journal history, use its requested period and pagination. The default asset view already includes a bounded raw-entry preview. For requested aggregate analysis, disclose any detail cap and keep totals from the complete aggregate, not the displayed sample. Read AssetAction history when a renewal explanation or explicit history request needs it; verify CategoryEnum/action meaning instead of treating an API Type as a commercial label.

## Present

For default asset views, use the raw-entry presentation above and stop. The following presentation is for separately requested deeper analysis. Display Asset.Name in the Asset column and follow the record-details and optional-link rules in [SKILL.md](../SKILL.md). Keep IDs internal unless explicitly requested. Duplicate names remain separate rows. For usage, add `Asset | Resource | Unit | Period | Granted | Consumed | Remaining`, and the journal count/date span. Missing data is `—`. Use two-decimal numeric display with exact values retained internally.

Factual usage and elapsed-term arithmetic can inform a discussion. Do not turn sparse demo records into a pace judgement or recommend a new commitment unless the user asks for a reasoned forecast and the available evidence supports it. The original six-journal/90-day threshold is not a platform rule or a universally sufficient forecast sample.
