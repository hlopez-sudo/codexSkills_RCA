# Renewal

## Use the existing selection

Reuse the selected assets and known current term. Batch compatible assets into one renewAssets request. Keep requested Anchor assets and source relationships; do not silently drop an asset after a failure or create one quote per asset.

A straightforward renewal does not need all entitlements, AssetAction history or lifetime journals as preflight. Read effective negotiated terms only when needed to carry or compare requested commercial terms. Use [reading](reading.md) for that scoped work.

## Create the requested renewal

```json
{
  "body": {
    "assetIds": ["<selected asset ids>"],
    "outputRecordType": "Quote"
  }
}
```

For an ordinary next-term renewal, omit optional renewalStartDate/renewalEndDate when the user did not specify a custom term. Salesforce derives the term from the applicable asset/contract renewal settings. If required settings are missing, resolve those specific settings; do not invent dates or silently patch the asset.

Explicit dates take precedence. Early and expired renewals require renewalStartDate; use the operation's full DateTime contract and the asset's time zone. Early renewal replaces the current term and requires the relevant product/feature support. Do not turn an ordinary renewal request into early renewal automatically.

Apply date rules only to the requested case. The usage-selling guide allows expired-asset renewal after expiry with a past start date, while the API input reference describes today's/future dates. If backdated expired renewal is requested, verify support for that operation instead of silently shifting the date or treating ordinary amendment rules as definitive. Ramped usage has separate today-only restrictions. Cancelled assets cannot be renewed.

Use explicit outputRecordType and honor the requested proposal/execution boundary. The documented direct-to-Order usage limitation in this skill is specific to amendments; do not generalize it to every lifecycle API without evidence.

## Verify the resulting quote

Read the returned header and lines together, using QuoteAction.SourceAssetId to map each source. Verify quantities and derived/requested dates. Preserve Renew actions. Renewal Quantity can be the full renewed quantity with StartQuantity zero; do not use amendment-delta arithmetic without confirming the actual semantics.

For requested like-for-like negotiated usage terms, compare the applicable source term with the corresponding quote-side grants/rates by asset, resource, unit and GrantType. A prior Renewal can be the current term; a future Amendment may not be effective. Do not use the latest row or highest historical amount blindly.

If the engine returns a catalog default instead of an established requested negotiated value, correct only the quote through the supported business transaction API and read it back. Disclose the material correction. Do not change live entitlements or shared catalog templates. When the intended value is ambiguous, resolve it instead of applying a hidden upward-only adjustment.

Do not perform consumption/history comparisons unless requested. Report the renewal quote and relevant new term/quantities; include verified commitment amounts only when relevant. A Monetary Commit amount is not an upfront price.

For authorized conversion/activation, use the Revenue Conversion skill and verify resulting ownership. A Draft renewal quote alone is not a completed renewal. Renewal behavior here is documentation guidance, not a new live test.
