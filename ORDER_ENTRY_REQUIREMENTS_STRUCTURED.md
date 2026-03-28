## 1. Overview

### 1.1 Purpose
- Define business requirements for a multi-instrument order entry system used by portfolio managers, advisors, and operations teams.
- Ensure order capture is consistent, auditable, and validated before submission.
- Standardize behavior across bonds, equities, options, and funds while preserving instrument-specific rules.

### 1.2 Scope
- In scope:
  - New order capture for buy and sell transactions.
  - Validation of mandatory fields, business rules, balances, and risk constraints.
  - Real-time calculation of derived values, including fees, accrued interest where relevant, and estimated settlement amount.
  - User-facing error handling and submission outcomes.
- Out of scope:
  - Post-trade settlement processing in external custodians.
  - Corporate action processing.
  - Advanced execution algorithms and smart order routing.

### 1.3 Supported Instruments
- Bond
- Equity
- Option
- Fund

## 2. Domain Model

### 2.1 Key Entities and Attributes

| Entity | Attribute | Type | Required | Description |
|---|---|---|---|---|
| Transaction | Transaction Id | String | Yes | Unique order identifier created on submit. |
| Transaction | Portfolio Id | String | Yes | Target portfolio for the order. |
| Transaction | Instrument Id | String | Yes | Internal identifier of selected instrument. |
| Transaction | Instrument Type | Enum | Yes | Bond, Equity, Option, Fund. |
| Transaction | Side | Enum | Yes | Buy or Sell. |
| Transaction | Order Type | Enum | Yes | Market or Limit. |
| Transaction | Trade Date | Date | Yes | Business date of order creation. |
| Transaction | Quantity | Decimal | Yes | Units, nominal, contracts, or shares depending on instrument. |
| Transaction | Limit Price | Decimal | Conditional | Required for Limit orders only. |
| Transaction | Price Input Mode | Enum | Yes | Price or Percentage, depends on instrument and config. |
| Transaction | Gross Amount | Decimal | Yes | Quantity multiplied by execution price basis. |
| Transaction | Fees Amount | Decimal | Yes | Total fees applied to order. |
| Transaction | Accrued Interest Amount | Decimal | Conditional | Relevant for bonds only. |
| Transaction | Net Amount | Decimal | Yes | Gross plus fees plus accrued interest based on side. |
| Transaction | Settlement Currency | String | Yes | Currency of settlement amount. |
| Transaction | Settlement Account Id | String | Yes | Account funding or receiving the transaction. |
| Transaction | Status | Enum | Yes | Draft, Validated, Rejected, Submitted. |
| Portfolio | Portfolio Id | String | Yes | Unique portfolio identifier. |
| Portfolio | Client Id | String | Yes | Owning client identifier. |
| Portfolio | Base Currency | String | Yes | Portfolio reporting currency. |
| Portfolio | Risk Profile | Enum | No | Optional profile used for soft risk checks. |
| Portfolio | Is Active | Boolean | Yes | Portfolio must be active for order entry. |
| Instrument | Instrument Id | String | Yes | Unique instrument identifier. |
| Instrument | Instrument Type | Enum | Yes | Bond, Equity, Option, Fund. |
| Instrument | Ticker or ISIN | String | Yes | Market identifier. |
| Instrument | Trading Currency | String | Yes | Currency used for trading and pricing. |
| Instrument | Smallest Trading Unit | Decimal | Yes | Minimum quantity increment. |
| Instrument | Minimum Order Size | Decimal | No | Optional minimum order quantity or nominal. |
| Instrument | Price Precision | Integer | Yes | Number of decimals allowed for price input. |
| Instrument | Quantity Precision | Integer | Yes | Number of decimals allowed for quantity input. |
| Instrument | Day Count Convention | Enum | Conditional | Required for interest-bearing bonds. |
| Instrument | Coupon Rate | Decimal | Conditional | Required for coupon-bearing bonds. |
| Instrument | Last Coupon Date | Date | Conditional | Required for accrued interest calculation where applicable. |
| Account | Account Id | String | Yes | Unique account identifier. |
| Account | Portfolio Id | String | Yes | Parent portfolio. |
| Account | Client Id | String | Yes | Owner client identifier. |
| Account | Account Type | Enum | Yes | Cash, Securities, Margin. |
| Account | Currency | String | Yes | Account currency. |
| Account | Available Balance | Decimal | Yes | Available amount for settlement and controls. |
| Account | Is Settlement Eligible | Boolean | Yes | Indicates if account can settle this order type. |
| Position | Portfolio Id | String | Yes | Parent portfolio for position. |
| Position | Instrument Id | String | Yes | Instrument of the position. |
| Position | Available Quantity | Decimal | Yes | Quantity available for sell. |
| Position | Pledged Quantity | Decimal | No | Quantity unavailable due to collateral. |
| Pricing | Instrument Id | String | Yes | Instrument used for calculations. |
| Pricing | Price Date | DateTime | Yes | Timestamp of used market price. |
| Pricing | Clean Price | Decimal | Yes | Price excluding accrued interest where relevant. |
| Pricing | FX Rate | Decimal | Conditional | Needed when settlement currency differs from pricing currency. |

## 3. Business Rules

### 3.1 Interest Calculation

| Rule Name | Description | Example |
|---|---|---|
| Interest-Bond-Only | Accrued interest applies to bonds only. Equities, options, and funds must return zero accrued interest. | Input: Equity buy 100 shares. Output: Accrued Interest = 0.00. |
| Interest-Day-Count | Accrued interest uses the instrument day count convention. Supported at minimum: Actual over Actual, 30E over 360, Actual over 360. | Input: Bond coupon 4 percent, nominal 100000, 45 accrued days, 30E over 360. Output: Accrued Interest = 100000 x 0.04 x 45 over 360 = 500.00. |
| Interest-Reference-Period | Accrued days are measured from last coupon date inclusive to trade date exclusive unless market standard states otherwise for the instrument. | Input: Last coupon 01-01, trade date 01-03. Output: Days accrued counted from 01-01 to 28-02. |
| Interest-Zero-Coupon | Zero-coupon bonds must not generate accrued coupon interest. | Input: Zero-coupon bond buy. Output: Accrued Interest = 0.00. |
| Interest-Negative-Guard | Accrued interest cannot be negative. If calculation returns negative due to bad dates, order is invalid. | Input: Trade date before last coupon date. Output: Invalid with interest date error. |
| Interest-Ex-Coupon-Window | If trade date is inside ex-coupon window and market rule says buyer does not receive upcoming coupon, accrued interest follows market rule configuration. | Input: Trade date in ex-coupon period. Output: Accrued interest adjusted or set to zero according to configuration. |

### 3.2 Transaction Calculation

| Rule Name | Description | Example |
|---|---|---|
| Calc-Gross-Amount | Gross Amount equals Quantity multiplied by price basis. For bonds with percentage pricing, price basis equals nominal x price percent over 100. | Input: Bond nominal 200000 at 101.25 percent. Output: Gross Amount = 202500.00. |
| Calc-Fees | Fees are computed using configured tariff model and may include broker fee, exchange fee, and fixed fee components. | Input: Gross 100000, fee 0.10 percent plus fixed 5. Output: Fees = 105.00. |
| Calc-Net-Buy | Net Amount for buy equals Gross plus Fees plus Accrued Interest. | Input: Gross 202500, Fees 105, Accrued 500. Output: Net Buy = 203105.00. |
| Calc-Net-Sell | Net Amount for sell equals Gross minus Fees plus or minus Accrued Interest based on market convention for sold bond. | Input: Gross 202500, Fees 105, Accrued receivable 500. Output: Net Sell = 202895.00. |
| Calc-Rounding-Currency | Monetary outputs are rounded to settlement currency precision using half-up rounding. | Input: USD amount 10.005. Output: 10.01. |
| Calc-Rounding-Quantity | Quantity input is rounded only if allowed by instrument precision. Otherwise, order is invalid. | Input: Equity quantity 10.123 with precision 0. Output: Invalid quantity precision. |
| Calc-FX-Conversion | If pricing currency differs from settlement currency, apply latest eligible FX rate as of trade date. | Input: EUR price, USD settlement, FX 1.10. Output: Net Amount USD = Net EUR x 1.10. |

### 3.3 Validations

| Rule Name | Description | Example |
|---|---|---|
| Val-Required-Fields | Portfolio, instrument, side, order type, quantity, and settlement account are mandatory. Limit price is mandatory for limit orders only. | Input: Limit order without limit price. Output: Invalid. |
| Val-Field-Format | Numeric fields must accept decimal point and decimal comma and normalize to canonical decimal format. | Input: Limit 100,25. Output: Parsed as 100.25 valid. |
| Val-Positive-Quantity | Quantity must be strictly greater than zero. | Input: Quantity 0. Output: Invalid. |
| Val-Price-Range | Price must be within allowed instrument range when defined. | Input: Bond limit 450 percent with max 250 percent. Output: Invalid. |
| Val-Trading-Unit | Quantity must be multiple of smallest trading unit. | Input: Unit 0.01, entered 10.005. Output: Invalid. |
| Val-Minimum-Order-Size | Quantity or nominal must meet minimum order size when configured. | Input: Min 1000 nominal, entered 900. Output: Invalid. |
| Val-Cross-Side-Position | Sell quantity must not exceed available position after pledged amount and pending sells. | Input: Available 100, pending sell 30, new sell 80. Output: Invalid because net available is 70. |
| Val-Cross-Limit-Market | Market orders must not carry limit price; limit orders must carry limit price. | Input: Market with limit price 99.0. Output: Invalid. |
| Val-Trade-Date | Trade date must be business day or must follow explicit holiday override rule. | Input: Trade date on market holiday with no override. Output: Invalid. |
| Val-Instrument-Eligibility | Instrument must be active and tradeable for selected portfolio and client restrictions. | Input: Suspended instrument. Output: Invalid. |

### 3.4 Balance and Risk Controls

| Rule Name | Description | Example |
|---|---|---|
| Risk-Insufficient-Cash-Buy | For buy orders, available cash in settlement account must cover estimated net amount plus reserve buffer if configured. | Input: Net buy 50000, available 49000. Output: Rejected for insufficient balance. |
| Risk-Insufficient-Position-Sell | For sell orders, available quantity must be sufficient after considering blocks and pending trades. | Input: Available 50, entered sell 60. Output: Rejected for insufficient position. |
| Risk-Concentration-Limit | Optional concentration check: post-trade weight by issuer, sector, or instrument must not exceed configured threshold. | Input: Post-trade issuer weight 27 percent with max 25 percent. Output: Rejected. |
| Risk-Notional-Limit | Optional notional limit per order and per day must be enforced. | Input: Order notional 2.5 million, daily max 2 million. Output: Rejected. |
| Risk-Warning-Versus-Block | Each control is classified as blocking or warning. Blocking stops submission, warning allows submit with user acknowledgement when policy permits. | Input: Soft profile breach. Output: Warning shown, submit allowed after acknowledgement. |

### 3.5 Settlement Rules

| Rule Name | Description | Example |
|---|---|---|
| Settle-Allowed-Accounts | Settlement account must be in selected portfolio and client ownership and marked settlement-eligible. | Input: Account from another client. Output: Invalid. |
| Settle-Currency-Choice | If instrument currency equals portfolio base currency, system auto-selects matching settlement account and disallows manual override. | Input: Instrument EUR, portfolio EUR. Output: EUR account auto-selected and locked. |
| Settle-Multi-Currency | If instrument currency differs from portfolio base currency, user may select only instrument currency account or portfolio base currency account, when both exist. | Input: Instrument USD, portfolio EUR, USD and EUR cash accounts exist. Output: Only USD or EUR selectable. |
| Settle-No-Eligible-Account | If no eligible account exists, submission is blocked and user receives account setup guidance. | Input: Instrument GBP, only EUR account exists, policy requires GBP settlement. Output: Invalid with setup message. |
| Settle-Same-Client-Constraint | Funding and receiving accounts must belong to same client unless explicit transfer mandate exists. | Input: Cross-client account selected. Output: Invalid. |

### 3.6 UI Behaviour Rules

| Rule Name | Description | Example |
|---|---|---|
| UI-Conditional-Fields | UI displays fields by context. Limit Price appears only for limit orders. Accrued Interest display appears only for bonds. | Input: Equity market order. Output: No limit field, no accrued-interest field. |
| UI-Default-Side | Default side may be prefilled from originating screen context, else no default is forced. | Input: Opened from holdings sell action. Output: Side defaults to Sell. |
| UI-Default-Order-Type | Default order type is Market unless policy or instrument dictates otherwise. | Input: New equity order. Output: Order Type = Market. |
| UI-Derived-Fields-ReadOnly | Gross, Fees, Accrued Interest, and Net are system-derived and read-only. | Input: User edits net amount. Output: Not allowed. |
| UI-Reset-On-Instrument-Change | Changing instrument clears dependent fields and recalculates constraints and defaults. | Input: Switch from bond to option. Output: Quantity unit, price mode, and settlement choices refreshed. |
| UI-Reset-On-Side-Change | Changing side recomputes sign-sensitive fields and validations. | Input: Buy changed to Sell. Output: Position validation replaces cash validation precedence. |
| UI-Real-Time-Feedback | Validation and derived calculations update after each relevant input change without requiring submission. | Input: Quantity changed. Output: Net amount and balance check refresh immediately. |

## 4. Process Flow

1. Determine portfolio context.
   - Use implicit context if launched from a portfolio-specific screen.
   - Require explicit portfolio selection if no context exists.
2. Select instrument.
   - User chooses from searchable list or receives prefilled instrument from prior screen.
   - System loads instrument metadata, current position, pricing references, and allowed settlement accounts.
3. Enter order details.
   - User sets side, order type, quantity, and conditional fields such as limit price.
   - System enforces instrument-specific units and display conventions.
4. Perform field-level validations.
   - Required checks, numeric format checks, precision checks, and range checks.
5. Perform cross-field and portfolio-level validations.
   - Position checks, balance checks, eligibility checks, and risk controls.
6. Calculate derived values.
   - Gross amount, fees, accrued interest, FX conversion, and net amount.
   - Apply rounding according to currency and quantity precision.
7. Present order summary.
   - Display all derived values and warnings.
   - Distinguish blocking errors from warnings.
8. Submit order.
   - If no blocking errors, create transaction record with Submitted status.
   - Persist audit-relevant input and derived outputs.
9. Return outcome to user.
   - On success, show confirmation with transaction id.
   - On failure, keep entered values where possible and highlight corrective actions.

## 5. Error Handling

### 5.1 Error Types
- Validation Error:
  - Input missing, malformed, out of range, or violating trading unit rules.
- Business Rule Error:
  - Violates balance, position, settlement, or risk constraints.
- Data Availability Error:
  - Missing price, missing FX rate, missing account eligibility data.
- Authorization Error:
  - User lacks permission for selected portfolio or instrument.
- Technical Error:
  - System, connectivity, or persistence failures.

### 5.2 User Feedback Rules
- Show clear message with:
  - what failed,
  - why it failed,
  - what user can do next.
- Field-level errors must be displayed near the relevant field.
- Cross-field or global errors must be displayed in a top-level error summary.
- Blocking errors prevent submission and keep the form editable.
- Warning messages do not block submission unless policy marks them as blocking.
- Technical errors must include a trace reference id for support and no internal stack details.

## 6. Assumptions

- Trade date uses portfolio market calendar unless instrument market calendar is explicitly configured.
- Latest available market data on or before trade date is acceptable for pre-trade calculations.
- Fee model is centrally configured and retrievable at order time.
- Settlement eligibility of accounts is pre-maintained by operations.
- For options and funds, quantity unit and price mode are instrument-configuration driven.
- Risk controls can be enabled per client or portfolio and classified as warning or blocking.
- Partial fills and post-submit lifecycle management are handled outside this order entry scope.

## 7. Open Questions

- Should market orders require a last-known price freshness threshold, and what is the threshold per instrument type?
- Which day count conventions are mandatory at go-live for bonds, and are market-specific overrides needed?
- For sell bond orders, how should accrued interest sign and settlement treatment be standardized across venues?
- Which risk checks are mandatory blockers versus warnings at launch?
- Should there be separate notional limits for asset classes and for individual traders?
- Is cross-currency settlement optional or mandatory when both instrument-currency and base-currency accounts exist?
- What is the exact policy for holiday handling and manual override approval workflow?
- Are short-selling and margin-enabled sells allowed for equities and options in scope?
- What audit fields are mandatory in the transaction record for regulatory reporting?
- Is dual approval required above a configurable notional threshold?