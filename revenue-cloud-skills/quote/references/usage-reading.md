# Read usage models and rates

For a usage-model or rate question about a Monetary Commit product, get the corresponding Anchor's catalog base rates and the associated percentage rate discounts on the Commit quote line. Present those two parts together.

Reuse the quote-line ID and Product2.UsageModelType already returned by creation. If absent, resolve them with one quote-scoped query.

1. Read the corresponding Anchor's active Base RateCardEntry rows for the applicable resources, selling model, currency and effective date. Retrieve all relevant resources in one query. Resolve the actual Anchor from available product context; shared resources alone are insufficient when multiple Anchors or rate cards match.
2. Read the selected Commit quote line's associated rateAdjustments through Quote Line Item Usage Details, using the requested effective date or quote start date:

   `GET /services/data/v68.0/commerce/quotes/line-items/{quoteLineItemId}/usage-details`

3. Check returned errors, match discounts to resources, and show the Anchor catalog rate, currency, consumption unit and associated Commit-line percentage discount. Preserve the API's adjustment meaning and sign convention. A commitment line's null base rate does not mean zero; the base rate comes from the Anchor.

Reuse resolved inputs and run independent reads together when possible. Do not add an Anchor line to explain pricing.

Only load [quote edits](usage-negotiation.md) when the user requests a change. Negotiated grants/commitments and rate overrides belong in that edit workflow. A routine rate question does not require grant queries, negotiation snapshots or a comparison of default and changed values.

Sources: [Anchor Product with Monetary Commitments](https://help.salesforce.com/s/articleView?id=ind.qocal_anchor_with_monetary_commit.htm&type=5&release=264), [Quote Line Item Usage Details](https://developer.salesforce.com/docs/revenue/revenue-management/guide/connect-resources-quote-usage-details.html).
