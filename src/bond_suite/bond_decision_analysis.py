from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, timedelta
from typing import Any

import pandas as pd


@dataclass
class BondPosition:
    purchase_date: date
    historical_cost_price_percent: float
    maturity_date: date
    coupon_rate_percent: float
    coupon_frequency_per_year: int
    nominal_value_position: float
    current_price_percent: float
    accrued_interest_current: float
    investment_currency: str
    account_currency: str
    current_fx_rate: float
    discount_rate_percent: float
    settlement_days: int


class BondCalculator:
    def __init__(self, position: BondPosition):
        self.position = position
        self.today = date.today()

    def validate_required_inputs(self) -> list[str]:
        raw = asdict(self.position)
        required_fields = [
            "purchase_date",
            "historical_cost_price_percent",
            "maturity_date",
            "coupon_rate_percent",
            "coupon_frequency_per_year",
            "nominal_value_position",
            "current_price_percent",
            "accrued_interest_current",
            "investment_currency",
            "account_currency",
            "current_fx_rate",
            "discount_rate_percent",
            "settlement_days",
        ]

        missing: list[str] = []
        for field_name in required_fields:
            if raw.get(field_name) is None:
                missing.append(field_name)

        if self.position.coupon_frequency_per_year <= 0:
            missing.append("coupon_frequency_per_year (must be > 0)")
        if self.position.nominal_value_position <= 0:
            missing.append("nominal_value_position (must be > 0)")
        if self.position.current_fx_rate <= 0:
            missing.append("current_fx_rate (must be > 0)")
        if self.position.maturity_date <= self.today:
            missing.append("maturity_date (must be after today)")
        if self.position.maturity_date <= self.position.purchase_date:
            missing.append("maturity_date (must be after purchase_date)")
        if self.position.account_currency.upper() != "EUR":
            missing.append("account_currency (must be EUR)")

        return sorted(set(missing))

    def _to_eur(self, amount_investment_ccy: float) -> float:
        if self.position.investment_currency.upper() == self.position.account_currency.upper():
            return amount_investment_ccy
        return amount_investment_ccy * self.position.current_fx_rate

    def _discount_factor(self, cashflow_date: date) -> float:
        if cashflow_date <= self.today:
            return 1.0
        years = (cashflow_date - self.today).days / 365.0
        discount_rate = self.position.discount_rate_percent / 100.0
        return 1.0 / ((1.0 + discount_rate) ** years)

    def _historical_purchase_value_eur(self) -> float:
        purchase_value_inv = self.position.nominal_value_position * (self.position.historical_cost_price_percent / 100.0)
        return self._to_eur(purchase_value_inv)

    def generate_coupon_schedule(self) -> pd.DataFrame:
        months = max(1, int(round(12 / self.position.coupon_frequency_per_year)))
        coupon_amount_inv = (
            self.position.nominal_value_position
            * (self.position.coupon_rate_percent / 100.0)
            / self.position.coupon_frequency_per_year
        )

        dates: list[date] = []
        d = self.position.maturity_date
        while d > self.today:
            dates.append(d)
            d = (pd.Timestamp(d) - pd.DateOffset(months=months)).date()

        rows: list[dict[str, Any]] = []
        for coupon_date in sorted(dates):
            is_maturity = coupon_date == self.position.maturity_date
            rows.append(
                {
                    "cashflow_date": coupon_date,
                    "coupon_amount_investment_ccy": coupon_amount_inv,
                    "redemption_amount_investment_ccy": self.position.nominal_value_position if is_maturity else 0.0,
                    "total_cashflow_investment_ccy": coupon_amount_inv
                    + (self.position.nominal_value_position if is_maturity else 0.0),
                }
            )

        return pd.DataFrame(rows)

    def calculate_sell_value(self) -> pd.DataFrame:
        settlement_date = self.today + timedelta(days=max(0, self.position.settlement_days))
        purchase_value_eur = self._historical_purchase_value_eur()

        rows: list[dict[str, Any]] = []
        for shift in (-0.5, 0.0, 0.5):
            price_percent = self.position.current_price_percent + shift
            clean_price_inv = self.position.nominal_value_position * (price_percent / 100.0)
            sale_proceeds_inv = clean_price_inv + self.position.accrued_interest_current
            sale_proceeds_eur = self._to_eur(sale_proceeds_inv)
            discount_factor = self._discount_factor(settlement_date)
            pv_sale_eur = sale_proceeds_eur * discount_factor

            rows.append(
                {
                    "scenario": f"SELL_{shift:+.1f}pp",
                    "price_percent_assumption": price_percent,
                    "settlement_date": settlement_date,
                    "clean_price_investment_ccy": clean_price_inv,
                    "accrued_interest_investment_ccy": self.position.accrued_interest_current,
                    "sale_proceeds_investment_ccy": sale_proceeds_inv,
                    "sale_proceeds_eur": sale_proceeds_eur,
                    "discount_factor": discount_factor,
                    "present_value_eur": pv_sale_eur,
                    "profit_loss_vs_historical_purchase_eur": pv_sale_eur - purchase_value_eur,
                }
            )

        return pd.DataFrame(rows)

    def calculate_hold_cashflows(self) -> pd.DataFrame:
        coupon_schedule = self.generate_coupon_schedule()
        if coupon_schedule.empty:
            return pd.DataFrame(
                columns=[
                    "cashflow_date",
                    "cashflow_type",
                    "cashflow_investment_ccy",
                    "cashflow_eur",
                ]
            )

        rows: list[dict[str, Any]] = []
        for _, row in coupon_schedule.iterrows():
            flow_date = pd.to_datetime(row["cashflow_date"]).date()
            coupon_amount = float(row["coupon_amount_investment_ccy"])
            redemption_amount = float(row["redemption_amount_investment_ccy"])

            rows.append(
                {
                    "cashflow_date": flow_date,
                    "cashflow_type": "coupon",
                    "cashflow_investment_ccy": coupon_amount,
                    "cashflow_eur": self._to_eur(coupon_amount),
                }
            )

            if redemption_amount > 0:
                rows.append(
                    {
                        "cashflow_date": flow_date,
                        "cashflow_type": "redemption",
                        "cashflow_investment_ccy": redemption_amount,
                        "cashflow_eur": self._to_eur(redemption_amount),
                    }
                )

        return pd.DataFrame(rows)

    def discount_cashflows(self, cashflows: pd.DataFrame) -> pd.DataFrame:
        if cashflows.empty:
            return cashflows.copy()

        discounted = cashflows.copy()
        discounted["discount_factor"] = discounted["cashflow_date"].apply(
            lambda d: self._discount_factor(pd.to_datetime(d).date())
        )
        discounted["present_value_eur"] = discounted["cashflow_eur"] * discounted["discount_factor"]
        return discounted

    def compare_scenarios(self) -> dict[str, Any]:
        missing_fields = self.validate_required_inputs()
        if missing_fields:
            return {
                "scenario_summary": {
                    "status": "missing_required_inputs",
                    "missing_fields": missing_fields,
                },
                "sell_results": pd.DataFrame(),
                "hold_results": {},
                "discounted_cashflows_table": pd.DataFrame(),
                "final_decision": {
                    "statement": "Missing required input fields; analysis not executed.",
                    "better_option": None,
                },
                "analyse_page": pd.DataFrame(),
            }

        purchase_value_eur = self._historical_purchase_value_eur()

        sell_results = self.calculate_sell_value()
        sell_now_row = sell_results.iloc[(sell_results["price_percent_assumption"] - self.position.current_price_percent).abs().argmin()]

        hold_cashflows = self.calculate_hold_cashflows()
        discounted_hold_cashflows = self.discount_cashflows(hold_cashflows)
        hold_present_value_eur = (
            float(discounted_hold_cashflows["present_value_eur"].sum()) if not discounted_hold_cashflows.empty else 0.0
        )

        hold_results = {
            "remaining_coupons_investment_ccy": float(
                hold_cashflows.loc[hold_cashflows["cashflow_type"] == "coupon", "cashflow_investment_ccy"].sum()
            )
            if not hold_cashflows.empty
            else 0.0,
            "redemption_value_investment_ccy": float(
                hold_cashflows.loc[hold_cashflows["cashflow_type"] == "redemption", "cashflow_investment_ccy"].sum()
            )
            if not hold_cashflows.empty
            else 0.0,
            "discounted_value_total_eur": hold_present_value_eur,
            "profit_loss_vs_historical_purchase_eur": hold_present_value_eur - purchase_value_eur,
        }

        sell_profit_loss_eur = float(sell_now_row["profit_loss_vs_historical_purchase_eur"])
        hold_profit_loss_eur = float(hold_results["profit_loss_vs_historical_purchase_eur"])
        difference_eur = hold_profit_loss_eur - sell_profit_loss_eur

        better_option = "HOLD" if hold_present_value_eur > float(sell_now_row["present_value_eur"]) else "SELL"
        statement = (
            "Based on the current data, holding until maturity is financially better."
            if better_option == "HOLD"
            else "Based on the current data, selling today is financially better."
        )

        scenario_summary = {
            "better_option": better_option,
            "sell_now_present_value_eur": round(float(sell_now_row["present_value_eur"]), 6),
            "hold_present_value_eur": round(hold_present_value_eur, 6),
            "difference_hold_minus_sell_eur": round(
                hold_present_value_eur - float(sell_now_row["present_value_eur"]),
                6,
            ),
            "discount_rate_percent": self.position.discount_rate_percent,
            "decision_basis": "Only cashflows from today onward, discounted to today.",
        }

        final_decision = {
            "statement": statement,
            "better_option": better_option,
            "profit_loss_sell_today_eur": round(sell_profit_loss_eur, 6),
            "profit_loss_hold_to_maturity_eur": round(hold_profit_loss_eur, 6),
            "difference_hold_minus_sell_eur": round(difference_eur, 6),
        }

        analyse_page = self._build_analyse_page(
            sell_results=sell_results,
            coupon_schedule=self.generate_coupon_schedule(),
            discounted_cashflows_table=discounted_hold_cashflows,
            final_decision=final_decision,
            scenario_summary=scenario_summary,
        )

        return {
            "scenario_summary": scenario_summary,
            "sell_results": sell_results,
            "hold_results": hold_results,
            "discounted_cashflows_table": discounted_hold_cashflows,
            "final_decision": final_decision,
            "analyse_page": analyse_page,
        }

    def run_analysis(self) -> dict[str, Any]:
        return self.compare_scenarios()

    def _build_analyse_page(
        self,
        sell_results: pd.DataFrame,
        coupon_schedule: pd.DataFrame,
        discounted_cashflows_table: pd.DataFrame,
        final_decision: dict[str, Any],
        scenario_summary: dict[str, Any],
    ) -> pd.DataFrame:
        sections: list[pd.DataFrame] = []
        sections.append(pd.DataFrame([{"Section": "1) Input data used"}]))
        sections.append(pd.DataFrame([asdict(self.position)]))
        sections.append(pd.DataFrame([{}]))

        sections.append(pd.DataFrame([{"Section": "2) Sale calculation"}]))
        sections.append(sell_results)
        sections.append(pd.DataFrame([{}]))

        sections.append(pd.DataFrame([{"Section": "3) Remaining coupon schedule"}]))
        sections.append(coupon_schedule)
        sections.append(pd.DataFrame([{}]))

        sections.append(pd.DataFrame([{"Section": "4) Discounted cashflow table"}]))
        sections.append(discounted_cashflows_table)
        sections.append(pd.DataFrame([{}]))

        sections.append(pd.DataFrame([{"Section": "5) Final comparison"}]))
        sections.append(pd.DataFrame([scenario_summary]))
        sections.append(pd.DataFrame([final_decision]))

        return pd.concat(sections, ignore_index=True, sort=False)


def generate_coupon_schedule(position: BondPosition) -> pd.DataFrame:
    return BondCalculator(position).generate_coupon_schedule()


def calculate_sell_value(position: BondPosition) -> pd.DataFrame:
    return BondCalculator(position).calculate_sell_value()


def calculate_hold_cashflows(position: BondPosition) -> pd.DataFrame:
    return BondCalculator(position).calculate_hold_cashflows()


def discount_cashflows(position: BondPosition, cashflows: pd.DataFrame) -> pd.DataFrame:
    return BondCalculator(position).discount_cashflows(cashflows)


def compare_scenarios(position: BondPosition) -> dict[str, Any]:
    return BondCalculator(position).compare_scenarios()


# Backward-compatibility wrappers

def calculate_remaining_cashflows(position: BondPosition) -> pd.DataFrame:
    return calculate_hold_cashflows(position)


def calculate_npv_hold(position: BondPosition) -> dict[str, float]:
    discounted = discount_cashflows(position, calculate_hold_cashflows(position))
    value = float(discounted["present_value_eur"].sum()) if not discounted.empty else 0.0
    return {
        "future_cashflows_pv_eur": value,
        "decision_npv_eur": value,
    }


def calculate_sell_scenario(position: BondPosition) -> pd.DataFrame:
    return calculate_sell_value(position)


def calculate_effective_return(
    initial_outflow_eur: float,
    total_inflows_eur: float,
    start_date: date,
    end_date: date,
) -> dict[str, float]:
    total_profit = total_inflows_eur - initial_outflow_eur
    years = max((end_date - start_date).days / 365.0, 1e-9)
    if initial_outflow_eur <= 0 or total_inflows_eur <= 0:
        annualized_return_percent = float("nan")
    else:
        annualized_return_percent = (((total_inflows_eur / initial_outflow_eur) ** (1.0 / years)) - 1.0) * 100.0
    return {
        "profit_loss_eur": float(total_profit),
        "annualized_return_percent": float(annualized_return_percent),
        "holding_years": float(years),
    }


def calculate_ytm(position: BondPosition) -> float:
    calculator = BondCalculator(position)
    cashflows = calculator.calculate_hold_cashflows()
    if cashflows.empty:
        return float("nan")

    grouped = cashflows.groupby("cashflow_date", as_index=False)["cashflow_investment_ccy"].sum()
    cashflow_dates = [pd.to_datetime(d).date() for d in grouped["cashflow_date"].tolist()]
    cashflow_amounts = [float(v) for v in grouped["cashflow_investment_ccy"].tolist()]

    settlement_date = calculator.today + timedelta(days=max(0, position.settlement_days))
    dirty_price_inv = (
        position.nominal_value_position * (position.current_price_percent / 100.0)
        + position.accrued_interest_current
    )
    times = [max((d - settlement_date).days / 365.0, 0.0) for d in cashflow_dates]

    def f(rate: float) -> float:
        return sum(cf / ((1.0 + rate) ** t) for cf, t in zip(cashflow_amounts, times)) - dirty_price_inv

    def fp(rate: float) -> float:
        return sum((-t * cf) / ((1.0 + rate) ** (t + 1.0)) for cf, t in zip(cashflow_amounts, times))

    rate = max(position.coupon_rate_percent / 100.0, 0.01)
    for _ in range(80):
        value = f(rate)
        if abs(value) < 1e-10:
            return rate * 100.0
        deriv = fp(rate)
        if deriv == 0:
            break
        next_rate = rate - (value / deriv)
        if next_rate <= -0.999:
            next_rate = -0.999
        if abs(next_rate - rate) < 1e-12:
            return next_rate * 100.0
        rate = next_rate

    return rate * 100.0
