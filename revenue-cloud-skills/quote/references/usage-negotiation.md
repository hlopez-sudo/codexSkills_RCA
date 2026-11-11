# Optional quote edits

Read this only for requested edits. Basic creation does not load this reference or query its usage children. Use live quote-side rows, not catalog defaults, as the current commercial state.

When using Usage Details during an edit, use usageResourceGrantAndPolicyDetail.negotiatedGrantDetail.quantity for the current grant or commitment amount. The top-level quantity and catalog grantDetail.quantity can still show defaults after a change. Resolve quote-side record IDs before updating them.

## Quantity, discount, add and remove

Use the same direct Headless Place Sales Transaction POST as creation, with a parent Quote PATCH first and only the requested line changes. For quantity or discount, append a QuoteLineItem PATCH with its existing `attributes.id` and `Quantity` or `Discount`. For add, append a line POST with the existing QuoteId and required product/term/billing fields. For remove, append a line DELETE with its existing ID. Use `pricingPref: Force`, `taxPref: Skip`, `catalogRatesPref: Skip` for ordinary edits, and one read-back. The transaction reprices; do not run a separate pricing operation.

Resolve existing line IDs within the intended quote. Adding usage to an already negotiated quote needs fetch scoping that preserves existing negotiations; do not blindly refetch all catalog data.

## Resolve and snapshot the quote-side targets

```sql
SELECT Id, QuoteLineItemId, UsageResourceId, UsageResource.Name,
       UsageResource.Category, GrantType, GrantQuantity,
       ValidityPeriodTerm, ValidityPeriodUnit
FROM QuotLineItmUseRsrcGrant
WHERE QuoteLineItem.QuoteId = '<quote ID>'

SELECT Id, QuoteLineItemId, RateCardEntryId, RateCardEntry.RateCardType,
       RateCardEntry.UsageResourceId, RateCardEntry.UsageResource.Name,
       RateCardEntry.UsageResource.DefaultUnitOfMeasure.Name,
       RateCardEntry.Rate, RateCardEntry.RateUnitOfMeasureName,
       NegotiatedRate, IsChosenRate
FROM QuoteLineRateCardEntry
WHERE QuoteLineItem.QuoteId = '<quote ID>'

SELECT Id, QuoteLineRateCardEntryId, AdjustmentType, AdjustmentValue,
       LowerBound, UpperBound
FROM QuoteLineRateAdjustment
WHERE QuoteLineRateCardEntry.QuoteLineItem.QuoteId = '<quote ID>'
```

Join tiers to their quote rate entries by `QuoteLineRateCardEntryId`, then to the requested line/resource. Snapshot IDs, exact values, bounds, units, and untouched rows before editing. Refresh stale targets; do not create new rows merely because an amount differs.

| Requested change | Existing target and field |
|---|---|
| Monetary commitment | `QuotLineItmUseRsrcGrant.GrantQuantity`, with `GrantType = Commit` and the correct currency resource |
| Included usage allowance | `QuotLineItmUseRsrcGrant.GrantQuantity`, with `GrantType = Grant` and the correct usage resource/unit |
| Flat usage rate | Base `QuoteLineRateCardEntry.NegotiatedRate` |
| Tier adjustment | `QuoteLineRateAdjustment.AdjustmentValue` |

A product name is not a reliable type discriminator. Match the live usage model, resource category, currency and unit. Null negotiated rates do not mean zero. A tier-only product may have no flat-rate target. Do not fabricate one or add a companion product to make a rate table look complete.

## Apply the change

Use the [direct POST in SKILL.md](../SKILL.md), with the parent Quote PATCH first, `pricingPref: System`, `taxPref: Skip`, and `catalogRatesPref: Skip`. Append only the requested quote-side edits, for example:

```json
{
  "referenceId": "refCommit",
  "record": {
    "attributes": {
      "type": "QuotLineItmUseRsrcGrant",
      "method": "PATCH",
      "id": "<existing currency Commit ID>"
    },
    "GrantQuantity": 1250000
  }
}
```

For a tier edit, use `type: QuoteLineRateAdjustment`, its existing ID, and `AdjustmentValue`. For flat rates, use `type: QuoteLineRateCardEntry` and `NegotiatedRate`. Never substitute a commercial line discount for a usage-rate edit.

Preserve the existing rate structure and adjustment type. Distinguish an absolute value, percentage points, and a relative percentage. Establish the sign convention before interpreting an adjustment as a discount. Do not write computed effective rates.

Do not update catalog `RateCardEntry`, `RateAdjustmentByTier`, or `ProductUsageGrant` records. Skip catalog refetch during negotiation. For a new usage line on a previously negotiated quote, establish safe fetch scoping before using Fetch; the ordinary non-usage add test does not prove usage refetch preserves overrides.

## Verify and present

After completion, reread the same quote-scoped queries. Require exact target values, stable IDs and preserved unrelated rows/bounds. Reread line pricing to confirm ordinary charges remain correct. Report commitments separately from priced charges, and label rate denomination and consumption unit. Round only for display.

If the user also requested a proposal/PDF, continue to [document output](document-output.md) only after this verification succeeds. Generate from the persisted quote-side values. Do not reprice, refetch catalog rates, repeat the edits or reuse a pre-negotiation PDF as current. A later “Show me the updated PDF” request reuses this quote when it is unambiguous. Negotiation alone does not trigger document generation.

Live API checks on October 22, 2026 verified GPT Monetary Commit quantity, line Discount persistence, commitment amount, nonzero included allowance and percentage-tier adjustments, preserving unrelated usage rows. This product has zero-priced ordinary charges and tier-only usage rates: it cannot prove nonzero line-discount calculations or flat-rate edits. Policy edits, consumption rating and wallet drawdown were not tested. Detailed results are maintenance evidence, not required reading for routine quoting.
