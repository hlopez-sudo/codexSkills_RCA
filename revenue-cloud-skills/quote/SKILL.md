---
name: quote
description: Create and negotiate Salesforce Revenue Cloud quotes using Headless MCP, including quantity, discount, usage-rate and grant changes. Generate and deliver the configured proposal PDF with usage rate tiers through supported connected APIs or an existing local Salesforce session verified against the same org and user.
---

# Quote

For a document/proposal/PDF request on an existing quote, go directly to [document output](references/document-output.md). Generate only the selected `RLM_QuoteProposal_CS` proposal with usage rate tiers, retrieve its actual PDF, and attach it immediately after integrity checks. Reuse the current quote, completed pricing verification, and established same-org/user transport. The reference defines the exact org-scoped template, verified REST v68.0 helper, and recovery path. Use supported connected operations when available; reuse the known matching CLI fallback when MCP cannot generate/download, without repeating failed discovery. No routine PDF rendering, contact sheets, or visual review. For “create/update this quote and show the PDF,” verify the transaction first, then continue to document output.

For a basic quote: **look up required inputs, POST once, read back once, finish.** Aim for under 30 seconds when the connection responds normally. Build the payload in memory and execute dependent calls in one orchestration when possible. No local JSON files, Python helper, Apex, Tooling API, price audit, or repeated endpoint discovery.

## Required inputs only

Use Headless `dispatch_readonly`, `GET /services/data/v67.0/query`, with SOQL in `queryParams.q` and `userType: business`. Escape user-supplied literals. Run the following reads in parallel; reuse inputs already resolved in the current connected org.

```sql
SELECT Id,Name,CurrencyIsoCode,
 BillingStreet,BillingCity,BillingState,BillingPostalCode,BillingCountry,
 ShippingStreet,ShippingCity,ShippingState,ShippingPostalCode,ShippingCountry,
 (SELECT Id FROM Contacts LIMIT 1)
FROM Account WHERE Name='<account>' LIMIT 2

SELECT Id,Name,UsageModelType,
 (SELECT Id,UnitPrice,CurrencyIsoCode,Pricebook2Id,
  ProductSellingModel.SellingModelType,ProductSellingModel.PricingTermUnit
  FROM PricebookEntries
  WHERE IsActive=true AND Pricebook2.IsActive=true AND Pricebook2.IsStandard=true)
FROM Product2 WHERE IsActive=true AND Name IN ('<requested product>')

SELECT Id,Name FROM BillingTreatment WHERE Name='<applicable treatment>'
```

The product query includes the entry needed for the payload. Use its UnitPrice as returned; the transaction prices the quote. No separate price verification. Use the requested/existing price book, or Standard Price Book for new quotes in this org. Select entries matching the requested/account currency and selling model. Ask only for an actual ambiguity.

For new quotes on any account, default to `Billing Treatment - USA - Advance`, with Annual cadence for an annual model and Monthly for a monthly model. User-specified treatment or cadence takes precedence. Resolve the applicable treatment once and reuse it. Include a BillTo Contact on every new quote: set `BillToContactId` to the first contact returned for the selected account by the Contacts subquery above. If the account has no contacts, ask for a BillTo Contact before creating the quote. No prior-quote, channel, policy, identity or schema preflight.

Use the requested start date, or today in the user's timezone when omitted. A one-year annual line uses SubscriptionTerm 1 and end date one anniversary minus one day; six months on a monthly model uses 6. BillingFrequency is separate from term. Omit subscription fields for one-time products; do not invent an end date for evergreen products. Apply requested unit count to Quantity; explicitly monetary amounts belong to grants, not Quantity or UnitPrice.

## One direct POST

Headless **`dispatch`**, `userType: business`:

`POST /services/data/v68.0/connect/rev/sales-transaction/actions/place`

```json
{
  "pricingPref": "Force",
  "taxPref": "Skip",
  "configurationPref": {"configurationMethod": "Skip"},
  "graph": {
    "graphId": "createQuote",
    "records": [
      {"referenceId": "refQuote", "record": {
        "attributes": {"type": "Quote", "method": "POST"},
        "Name": "<quote name>", "QuoteAccountId": "<account ID>",
        "BillToContactId": "<first contact ID from the selected account>",
        "Pricebook2Id": "<entry's price book ID>", "CurrencyIsoCode": "<currency>",
        "Status": "Draft", "StartDate": "<start>"
      }},
      {"referenceId": "refLine0", "record": {
        "attributes": {"type": "QuoteLineItem", "method": "POST"},
        "QuoteId": "@{refQuote.id}", "Product2Id": "<product ID>",
        "PricebookEntryId": "<entry ID>", "UnitPrice": 15000, "Quantity": 2,
        "SubscriptionTerm": 1, "StartDate": "2026-10-22", "EndDate": "2027-10-21",
        "PeriodBoundary": "Anniversary", "BillingFrequency": "Annual",
        "BillingTreatmentId": "<treatment ID>"
      }}
    ]
  }
}
```

Substitute all example values. Copy non-null account billing/shipping address fields into the header. Add one line per requested product in the same graph. Include OpportunityId only when requested. For new quotes containing usage products, add `catalogRatesPref: Fetch` to initialize catalog data in the same call. Required bundle configuration is a separate path; optional configuration does not require extra work.

## One read-back, then finish

Require `isSuccess: true`, empty `errorResponse`, and `salesTransactionId`. Query the returned ID:

```sql
SELECT Id,QuoteNumber,Status,CalculationStatus,GrandTotal,BillToContactId,
 (SELECT Id,Product2Id,Product2.Name,Product2.UsageModelType,Quantity,StartDate,EndDate,TotalPrice FROM QuoteLineItems)
FROM Quote WHERE Id='<salesTransactionId>'
```

Verify `BillToContactId` matches the selected account contact. Retain the returned quote-line IDs and usage models for follow-up requests. Return the quote link, products, quantities and term. No routine progress narration or catalog-default explanation. Do not fetch all rates/grants during basic creation. Read the relevant grant only when its amount was requested or needs to be reported. Keep commitments separate from priced charges.

If proposal output was requested, continue to [document output](references/document-output.md) after this verification. Otherwise finish without generating or fetching a document. A user can request “Show me the proposal PDF” later; no additional confirmation is required for that requested generation. The document branch may use its helper, save a request journal, and store the retrieved PDF locally; the no-helper/no-local-files rules above apply to basic quote creation. If neither supported MCP operations nor a verified matching local session can complete the request, report the exact remaining limitation without a browser/link substitute.

On an actual failure, report its error; do not switch to Apex or start circular discovery. A timeout/ambiguous write needs one targeted existence check before any retry. Follow an async status only when the API returns one. Never claim a quote was not saved without evidence.

For usage-model or rate questions, read [usage reading](references/usage-reading.md). Start with the corresponding **Anchor** product's catalog base rates and the associated percentage rate discounts on the Commit quote line. Use Usage Details for those line-specific adjustments. Read negotiated grants/commitments and rate overrides only when the user requests edits. Do not add an Anchor line just to explain rates.

For later add/remove, quantity, discount or usage negotiation, read [quote edits](references/usage-negotiation.md) only when requested. Creation does not include approval, orders or activation. [Validation evidence](references/validation.md) is for maintenance, not required reading during quoting.
