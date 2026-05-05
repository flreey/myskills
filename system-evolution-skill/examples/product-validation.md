# Example: Product Validation

## User Problem

I built a tariff calculator website. How do I know if people will pay?

## Problem Type

Product / Startup.

## System Boundary

Inside:
- importers
- cross-border sellers
- freight forwarders
- tariff/HTS/AD-CVD data
- landing page
- report generation
- payment flow

Outside:
- macro trade policy changes
- Google algorithm changes
- legal responsibility of licensed customs brokers

## Information Layer

Inputs:
- product description
- HTS code if available
- origin country
- destination country
- duty/risk data
- user intent from search/query

Uncertainty:
- classification may be ambiguous
- data may be outdated
- user may only be curious, not willing to pay

## Energy / Resource Layer

Resources:
- developer time
- data quality
- user trust
- traffic
- payment infrastructure
- ability to generate credible reports

## Feedback Layer

Leading indicators:
- search started
- report preview viewed
- full report CTA clicked
- checkout started

Lagging indicators:
- payment completed
- repeat purchase
- report shared
- user asks for batch processing

## Failure Diagnosis

Likely failure points:
- users perceive calculator as a free commodity
- result lacks trust and source references
- audience is too broad
- no clear paid artifact

## Smallest Useful Experiment

Hypothesis:
Users will pay for a credible import duty and AD/CVD risk report, not for a generic calculator.

Action:
Add a $5 full report CTA to the result page.

Success metric:
At least 5% of completed searches click the report CTA, and at least one user pays or requests a sample report.

Failure metric:
Users search but do not click the report CTA.

Decision rule:
If clicks exist but payment is low, improve report sample and trust. If no clicks, reposition the offer.

## Evolution Roadmap

Keep:
- features that produce report CTA clicks

Remove:
- generic pages that attract traffic but no tool usage

Amplify:
- pages around AD/CVD risk and hidden duty exposure

Test next:
- one-off report vs monthly plan
