# Extended verification and provisioning

Read only for a requested usage-preservation check, an actual discrepancy, a lifecycle transaction needing additional mapping, or requested asset provisioning. Basic conversion and activation verification are in SKILL.md.

## Focused commercial verification

Saved quote usage rate records carry into order usage rate records. Do not make a full grant/policy/rate audit a prerequisite for ordinary conversion.

When asked to verify a negotiated commitment or rate discount, read the specific quote rows and corresponding order rows, scoped by quote-line/order-line lineage. Compare the requested values, resources, units and effective periods. Use transaction records, not the Anchor's current catalog rates.

Inspect unfamiliar optional relationships once if needed; reuse known schemas. Do not claim every usage term was preserved from a header, line total or successful action alone. Report a discrepancy before attempting repair.

For ramped/lifecycle transactions, compare the actual source structure and supported action/start/end quantity fields. Do not interpret amendment deltas as initial-sale quantities or require RampIdentifier/SegmentType to be null for every non-ramped order.

## Provision only when requested

Activated status proves activation, not asset creation. First establish whether the current order has source-correlated asset processing complete or pending. Use returned tracker/status details and actual Order/OrderItem-to-Asset or lifecycle-action mappings. An account-wide asset count cannot prove this order produced those assets.

Snapshot correlated asset/action/entitlement IDs and expected effects before submitting new work. If activation automation already submitted processing for this order, wait for that operation rather than submitting another.

If no work was submitted/completed and provisioning is authorized, call orderToAsset once. Its tool description requires a plain string ID:

```json
{"inputs":[{"orderId":"<activated order ID>"}]}
```

If the generated client schema instead requires an Order object and rejects the string before execution, treat this as an adapter mismatch. Use a described Headless business-action fallback if available; do not fabricate an object wrapper. If a request might already have run, inspect its tracker and source-linked records before another attempt.

Inspect every action result and business error. Follow the returned tracker, then verify source-linked asset quantities, lifecycle dates and requested entitlements. A timeout is pending work, not a reason to resend. An immediate empty query is not proof of failure; unchanged preexisting assets are not proof of success.

If correlation or processing state cannot be read, report the verified stage and what remains unknown. Do not synthesize Assets or patch entitlements through generic DML.

## Entitlements and lifecycle effects

TransactionUsageEntitlement rows can represent different periods, amendments, renewals or cancellations. Select by source asset, resource, unit, grant type and effective period using verified supersession rules. Do not sum every Commit row or assume newest CreatedDate means current commitment.

Verify requested monetary Commit and usage allowances against the originating quote/order and intended period. Keep quantity, priced charges and commitment size distinct. Inspect supported business repair paths when values differ.

An activated amendment or renewal can update existing assets. Verify the intended change on the correct source asset; zero new asset IDs does not prove failure.

Before retrying provisioning, inspect processing state and source-linked assets/actions. Resume only the missing stage, without replaying conversion or provisioning twice.
