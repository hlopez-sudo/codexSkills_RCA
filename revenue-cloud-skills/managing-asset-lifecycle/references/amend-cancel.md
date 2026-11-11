# Create amendment and cancellation quotes

## Amendment

Reuse the selected assets and known source context. For compatible assets, call amendAssets once:

```json
{
  "body": {
    "assetIds": ["<asset 1>", "<asset 2>", "<asset 3>"],
    "outputRecordType": "Quote",
    "amendmentStartDate": "<full ISO DateTime>",
    "quantityChange": 0
  }
}
```

quantityChange applies to every selected asset. Use zero when no quantity edit was requested; send a known common delta at creation to avoid a second write. A commitment amount is not a quantity delta. If per-asset deltas differ, create one compatible amendment and apply the requested changes with the [existing-amendment procedure](amendment-edit.md). Do not create one quote per asset by default.

Use amendAssets to initiate amendments. Place Sales Transaction edits the resulting transaction; it is not the API for creating asset lifecycle transactions. For usage products, outputRecordType must be Quote because the documented direct-to-Order amendment flow does not copy required usage records.

Check nested business success and the returned amendmentRecordId. Read the header and lines together using the query in [amendment editing](amendment-edit.md#one-read-for-header-actions-and-lines). Retain the QuoteAction IDs and source-asset mappings so a follow-up edit can use them immediately.

Present the quote reference and each selected line's Start Quantity, Quantity (change) and End Quantity using the [amendment presentation contract](amendment-edit.md#present-all-three-quantities). Include zero deltas on an unchanged amendment; all three columns remain visible.

A successful response may include requestId even when statusUrl is null and the quote is already available. That identifier alone is not a reason to poll. If the read shows pending calculation, poll only the header with bounded backoff. CompletedWithPricing or CompletedWithTax is not a reason to reprice. Do not load usage history, journals or all quote grants/rates for creation without a usage-term request.

## Effective dates

- Use the selected assets' stored time zone; all assets in one transaction must share it. Reuse verified source context. If absent, Salesforce uses UTC.
- For an immediate change with no explicit date, send the current ISO instant. Do not backdate to the user's local midnight.
- Honor a supplied future date and verify the saved line date. Non-ramped usage supports current/future changes; ramped usage lifecycle changes are restricted to today.
- Do not silently move a requested unsupported date. Preserve existing dates during later line edits.

The live future-dated test used January 1, 2027 for all three non-ramped assets. Applying the quantity edit later kept that date.

## Cancellation

Call cancelAssets with its typed body, selected assetIds, explicit outputRecordType and full cancellationDate. All assets in one cancellation request must use the same price book. A reduction that leaves a subscription active is an amendment.

Verify the returned record and its source mappings, effective date and cancellation result. Preserve the cancellation action; the amendment No Change → Amend gate does not apply. A cancellation quote does not prove that an asset is terminated. Continue through conversion/activation only when execution is authorized, then verify effective ownership.

Usage cancellation can prorate grants and forfeit unused grants. If an authorized live cancellation affects assets created the same day, consult Salesforce's consumption-object guidance for that case; do not perform entitlement cleanup merely for a Draft quote.

## Failure recovery

Use [MCP routing](mcp-routing.md) only for an actual error or capability gap. After an ambiguous create, check for an existing result before retrying; do not duplicate the lifecycle quote. A typed-tool failure is not a reason to try several guessed wrappers or to use a different API family.
