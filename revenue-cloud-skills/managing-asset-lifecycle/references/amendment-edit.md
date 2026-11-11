# View or edit an existing amendment

## One read for header, actions and lines

Reuse a sufficiently current verified read-back from this session. Otherwise query the exact quote once:

```sql
SELECT Id, QuoteNumber, Status, CalculationStatus,
       (SELECT Id, Product2Id, QuoteActionId, QuoteAction.SourceAssetId,
               QuoteAction.Type, StartQuantity, Quantity, EndQuantity,
               StartDate, EndDate
        FROM QuoteLineItems)
FROM Quote WHERE Id = '<quote id>'
```

Map each line to its asset through QuoteAction.SourceAssetId. Product IDs and array positions are insufficient when multiple assets share a product. Before an edit, confirm the target quote is editable and the selected line/action IDs belong to it. Query quote-side grants/rates only for requested edits to those values.

For a view-only request, read and present the requested amendment lines using the presentation contract below, then stop. Viewing an amendment does not require it to be editable and does not authorize an action transition or other write.

## Calculate the requested change once

For amendment lines:

- “Make it N”: desired EndQuantity = N.
- “Add N more”: desired EndQuantity = currently saved EndQuantity + N.
- Payload Quantity = desired EndQuantity − StartQuantity.

The API replaces the saved delta; it does not increment it. Start 1,000, current End 1,500, then “add 100” requires Quantity 600. Never write derived EndQuantity.

Retain the computed desired end quantities across retries. After a timeout, compare against those targets rather than adding N again to a possibly already-updated line. A new explicit user request to add more is a new edit.

## Apply the QuoteAction gate internally

| Saved action | Actual requested edit | Route |
|---|---|---|
| No Change | Yes | PATCH Type to Amend before line/child records in one Place graph. |
| Amend | Ordinary supported line changes | Batch updateLines; it already reprices. |
| No Change or Amend | Values already match | No write. |
| Renew, Cancel, Add or another action | Any | Preserve the action and use its own lifecycle semantics. |

For mixed No Change/Amend lines, use one graph for the requested changes and transition only the No Change actions. Deduplicate action IDs. Do not retry updateLines while the action is No Change, discover generic QuoteAction CRUD, or use Apex. The action transition is part of fulfilling the requested amendment; omit it from commentary and final responses.

## Tested Headless REST transaction

Use the session's verified Headless dispatch operation:

```text
POST /services/data/v68.0/connect/rev/sales-transaction/actions/place
```

For quantity changes requiring a transition, send this shape with resolved IDs and computed numeric deltas:

```json
{
  "pricingPref": "System",
  "taxPref": "Skip",
  "configurationPref": {"configurationMethod": "Skip"},
  "catalogRatesPref": "Skip",
  "graph": {
    "graphId": "amendmentRequestedChanges",
    "records": [
      {
        "referenceId": "parent",
        "record": {
          "attributes": {"type": "Quote", "method": "PATCH", "id": "<quote id>"}
        }
      },
      {
        "referenceId": "action0",
        "record": {
          "attributes": {"type": "QuoteAction", "method": "PATCH", "id": "<action id>"},
          "Type": "Amend"
        }
      },
      {
        "referenceId": "line0",
        "record": {
          "attributes": {"type": "QuoteLineItem", "method": "PATCH", "id": "<line id>"},
          "Quantity": 500
        }
      }
    ]
  }
}
```

For several lines, include the parent once, then all needed action PATCH records, then the requested line/child PATCH records. Preserve IDs, inherited dates and unrelated values. catalogRatesPref Skip avoids requesting catalog-rate replacement. These preferences were verified for the quantity transition; other requested edits must use their supported pricing/configuration contract.

Generic sObject PATCH of QuoteAction failed in this org even though describe marked it updateable. Use this transaction route directly. No Tooling Execute Anonymous or direct DML is needed.

For a requested commitment/rate edit, resolve the affected existing quote-side child IDs and use the Quote skill's supported payload. An absolute currency Commit amount belongs in the matching grant's GrantQuantity, not Quantity or UnitPrice. Apply this action gate before those child updates. The latest REST test covered quantities; it did not retest every grant/rate-edit combination. Preserve tier boundaries; do not introduce tier-boundary work.

## Verify once

Require HTTP success plus isSuccess true and no business errors. Read the same header/lines query and confirm:

- Same quote, line, action and source-asset IDs.
- Affected actions are Amend and the requested delta/end quantities are saved.
- Saved effective/end dates remain unchanged unless requested otherwise.
- Calculation has completed; poll only if it is actually pending.

Read requested child values when the edit involved them. Do not audit all commitments, tiers, policies or source entitlements for a quantity-only edit, or claim they were all verified. Usage grants can be prorated by the platform.

Do not issue updateLines or a standalone reprice after a successful Place graph already applied and priced the changes. If a write fails or times out, inspect persisted state and repair only missing work; a transaction graph is not a promise of rollback across every processing stage.

## Present all three quantities

For amendment creation or viewing, show every in-scope line. For a change confirmation, show each affected line, including when the requested edit was to a non-quantity field. Use the saved values from the read-back:

| Asset / line | Start Quantity | Quantity (change) | End Quantity |
|---|---:|---:|---:|
| <Asset.Name or meaningful line name> | 500 | +500 | 1,000 |

Start Quantity is the amendment's baseline; Quantity (change) is its saved delta; End Quantity is the resulting quantity. Show zero and signed changes, including reductions. Display each source asset using Asset.Name and follow the record-details and optional-link rules in [SKILL.md](../SKILL.md). Assets with the same name remain separate rows; do not expose raw or shortened Asset IDs as labels. Do not replace the table with only a before/after sentence, or present intended targets as saved values after an unsuccessful update.

On repeated edits, display the total saved amendment delta: Start 1,000 and prior End 1,500 followed by an additional 100 is Start Quantity 1,000, Quantity (change) +600, End Quantity 1,600. The latest requested increment of 100 is not the line's saved Quantity.

Include the quote reference and other requested business changes. Keep action updates and calculation status internal. The live asset remains unchanged until authorized downstream execution.
