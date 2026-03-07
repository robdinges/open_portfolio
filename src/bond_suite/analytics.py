from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Iterable

import numpy_financial as npf
import pandas as pd


class YieldBond:
    def __init__(
        self,
        face_value: float,
        coupon_rate: float,
        current_price: float,
        issue_date: str,
        maturity_date: str,
        payment_frequency: int,
    ):
        self.face_value = face_value
        self.coupon_rate = coupon_rate
        self.current_price = current_price
        self.issue_date = datetime.strptime(issue_date, "%Y-%m-%d")
        self.maturity_date = datetime.strptime(maturity_date, "%Y-%m-%d")
        self.payment_frequency = payment_frequency
        self.cash_flows = self._generate_cash_flows()

    def _generate_cash_flows(self) -> list[float]:
        years_to_maturity = (self.maturity_date - self.issue_date).days / 365
        total_payments = int(years_to_maturity * self.payment_frequency)
        cash_flows = [-self.current_price]

        for _ in range(max(total_payments - 1, 0)):
            cash_flows.append(self.face_value * self.coupon_rate / self.payment_frequency)

        cash_flows.append(
            self.face_value * self.coupon_rate / self.payment_frequency + self.face_value
        )
        return cash_flows

    def calculate_ytm(self) -> float | None:
        ytm = npf.irr(self.cash_flows)
        if pd.isna(ytm):
            return None
        return float(ytm) * self.payment_frequency


class TradeBond:
    def __init__(self, name: str, coupon_rate: float, start_date: date, end_date: date):
        self.name = name
        self.nominal_value = 0.0
        self.coupon_rate = coupon_rate
        self.end_date = end_date
        self.start_date = start_date
        self.purchase_date: date | None = None
        self.sale_date: date | None = None
        self.sale_price: float | None = None
        self.purchase_price: float | None = None

    def buy(
        self,
        nominal_value: float,
        purchase_date: date,
        purchase_price: float,
        calculate_cost: bool = False,
        cost_amount: float = 0,
    ) -> tuple[float, str]:
        purchase_value = nominal_value * purchase_price
        transaction_cost = (
            self.calculate_transaction_cost(purchase_value)
            if calculate_cost
            else cost_amount
        )
        accrued_interest = self.calculate_accrued_interest(purchase_date, nominal_value)
        total_purchase_amount = purchase_value + transaction_cost + accrued_interest

        specification = (
            f"Aankoopbedrag bond:\t{purchase_value:10.2f}\n"
            f"Transactiekosten:\t{transaction_cost:10.2f}\n"
            f"Meegekochte rente:\t{accrued_interest:10.2f}\n"
            f"Totaal af te rekenen:\t{total_purchase_amount:10.2f}\n"
        )

        self.nominal_value = nominal_value
        self.purchase_date = purchase_date
        self.purchase_price = purchase_price
        return total_purchase_amount, specification

    def sell(
        self,
        nominal_value: float,
        sale_date: date,
        sale_price: float,
        calculate_cost: bool = False,
        cost_amount: float = 0,
    ) -> tuple[float, str]:
        if nominal_value > self.nominal_value:
            raise ValueError("Niet genoeg nominale waarde om deze verkoop te doen.")

        self.nominal_value = nominal_value
        self.sale_date = sale_date
        self.sale_price = sale_price

        sale_value = nominal_value * sale_price
        transaction_cost = (
            self.calculate_transaction_cost(sale_value) if calculate_cost else cost_amount
        )
        accrued_interest = self.calculate_accrued_interest(sale_date, nominal_value)
        total_sale_amount = sale_value - transaction_cost + accrued_interest

        specification = (
            f"Verkoopbedrag bond:\t{sale_value:10.2f}\n"
            f"Transactiekosten:\t{transaction_cost:10.2f}\n"
            f"Meegekochte rente:\t{accrued_interest:10.2f}\n"
            f"Totaal af te rekenen:\t{total_sale_amount:10.2f}\n"
        )
        return total_sale_amount, specification

    @staticmethod
    def calculate_transaction_cost(value: float) -> float:
        transaction_cost = 1 + (0.001 * abs(value))
        return min(transaction_cost, 150)

    def calculate_accrued_interest(self, valuation_date: date, nominal_value: float) -> float:
        if valuation_date < self.start_date or (self.sale_date and valuation_date > self.sale_date):
            return 0
        days_held = (valuation_date - self.start_date).days
        return nominal_value * self.coupon_rate * (days_held / 365)


@dataclass
class ScenarioAction:
    transactie: str
    instrument: TradeBond
    nominale_waarde: float
    datum: date
    koers: float
    kosten_berekend: bool = False
    kosten_bedrag: float = 0


class Scenario:
    def __init__(self, scenario_name: str, actions: Iterable[ScenarioAction]):
        self.scenario_name = scenario_name
        self.actions = list(actions)
        self.opbrengst = 0.0

    def run(self) -> float:
        self.opbrengst = 0.0
        for action in self.actions:
            if action.transactie.upper() == "BUY":
                opbrengst, _ = action.instrument.buy(
                    action.nominale_waarde,
                    action.datum,
                    action.koers,
                    action.kosten_berekend,
                    action.kosten_bedrag,
                )
            elif action.transactie.upper() == "SELL":
                opbrengst, _ = action.instrument.sell(
                    action.nominale_waarde,
                    action.datum,
                    action.koers,
                    action.kosten_berekend,
                    action.kosten_bedrag,
                )
            else:
                raise ValueError(f"Onbekende transactie: {action.transactie}")
            self.opbrengst += opbrengst
        return self.opbrengst


def add_months(d: date, months: int) -> date:
    y = d.year + (d.month - 1 + months) // 12
    m = (d.month - 1 + months) % 12 + 1
    last_day = calendar.monthrange(y, m)[1]
    day = min(d.day, last_day)
    return date(y, m, day)


def yearfrac(d1: date, d2: date, methode: str = "ACT/ACT") -> float:
    if methode.upper() == "30/360":
        d1_day, d1_month, d1_year = d1.day, d1.month, d1.year
        d2_day, d2_month, d2_year = d2.day, d2.month, d2.year
        if d1_day == 31:
            d1_day = 30
        if d2_day == 31 and d1_day == 30:
            d2_day = 30
        return (
            (d2_year - d1_year) * 360
            + (d2_month - d1_month) * 30
            + (d2_day - d1_day)
        ) / 360.0
    return (d2 - d1).days / 365.0


def coupon_schedule(settlement: date, maturity: date, freq: int) -> list[date]:
    months = 12 // freq
    d = maturity
    dates: list[date] = []
    while d > settlement:
        dates.append(d)
        d = add_months(d, -months)
    return sorted(dates)


def last_next_coupon(settlement: date, maturity: date, freq: int) -> tuple[date, date]:
    months = 12 // freq
    d = maturity
    while d > settlement:
        prev = add_months(d, -months)
        if prev <= settlement:
            return prev, d
        d = prev
    return maturity, maturity


class PortfolioBond:
    def __init__(
        self,
        isin: str = "leeg",
        naam: str = "leeg",
        valuta: str = "EUR",
        nominale_waarde: float = 1000.0,
        couponrente_pct: float = 0.0,
        aankoop_koers_pct: float = 100.0,
        einddatum: date | None = None,
        settlement_datum: date | None = None,
        valutakoers: float = 1.0,
        aankoopkosten: float | None = None,
        broker: str | None = None,
        coupon_freq_pa: int = 1,
        berekeningswijze: str = "ACT/ACT",
    ):
        self.isin = isin
        self.naam = naam
        self.valuta = valuta
        self.nominale_waarde = nominale_waarde
        self.couponrente_pct = couponrente_pct
        self.aankoop_koers_pct = aankoop_koers_pct
        self.einddatum = einddatum
        self.settlement_datum = settlement_datum or date.today()
        self.broker = broker
        self.valutakoers = valutakoers
        self.aankoopkosten = aankoopkosten
        self.coupon_freq_pa = coupon_freq_pa
        self.berekeningswijze = berekeningswijze

    def settlement(self) -> date:
        return self.settlement_datum + timedelta(days=2)

    def coupon_bedrag(self) -> float:
        return self.nominale_waarde * (self.couponrente_pct / 100.0) / self.coupon_freq_pa

    def jaarlijkse_coupon(self) -> float:
        return self.nominale_waarde * (self.couponrente_pct / 100.0)

    def leningbedrag(self) -> float:
        return self.nominale_waarde * (self.aankoop_koers_pct / 100.0)

    def bereken_aankoopkosten(self) -> float:
        if pd.isna(self.aankoopkosten) or self.aankoopkosten is None:
            if self.broker == "VLK":
                return (
                    0.001
                    * (self.nominale_waarde + self.accrued_interest())
                    / self.valutakoers
                    * (self.aankoop_koers_pct / 100.0)
                )
            if self.broker == "ING":
                return 1 + (
                    0.001
                    * (self.nominale_waarde + self.accrued_interest())
                    / self.valutakoers
                    * (self.aankoop_koers_pct / 100.0)
                )
            return 0.0
        return float(self.aankoopkosten)

    def accrued_interest(self, peildatum: date | None = None) -> float:
        if self.einddatum is None:
            return 0.0
        d_settle = self.settlement() if peildatum is None else peildatum
        last_coup, next_coup = last_next_coupon(d_settle, self.einddatum, self.coupon_freq_pa)
        if d_settle <= last_coup:
            return 0.0
        period = yearfrac(last_coup, next_coup, self.berekeningswijze)
        if period <= 0:
            return 0.0
        frac = yearfrac(last_coup, d_settle, self.berekeningswijze) / period
        return self.coupon_bedrag() * frac

    def totale_investering(self) -> float:
        return (
            (self.leningbedrag() + self.accrued_interest()) / self.valutakoers
            + self.bereken_aankoopkosten()
        )

    def dirty_price(self) -> float:
        return self.leningbedrag() + self.accrued_interest()

    def cashflows(self) -> list[tuple[date, float]]:
        if self.einddatum is None:
            return []
        flows: list[tuple[date, float]] = []
        for d in coupon_schedule(self.settlement(), self.einddatum, self.coupon_freq_pa):
            amt = self.coupon_bedrag()
            if d == self.einddatum:
                amt += self.nominale_waarde
            flows.append((d, amt))
        return flows

    def ytm(self) -> float:
        dirty = self.dirty_price()
        flows = self.cashflows()
        if not flows:
            return float("nan")

        t = [yearfrac(self.settlement(), d) for d, _ in flows]
        a = [amt for _, amt in flows]

        def f(r: float) -> float:
            return sum(amt / (1 + r) ** ti for amt, ti in zip(a, t)) - dirty

        def fp(r: float) -> float:
            return sum(-ti * amt / (1 + r) ** (ti + 1) for amt, ti in zip(a, t))

        r = max(self.couponrente_pct / 100.0, 0.02)
        for _ in range(50):
            val = f(r)
            if abs(val) < 1e-8:
                return r * 100
            der = fp(r)
            if der == 0:
                break
            r_new = r - val / der
            if abs(r_new - r) < 1e-10:
                return r_new * 100
            r = r_new
        return r * 100


class MarketDataStore:
    def __init__(self):
        self.df_obligatiekoersen = pd.DataFrame(columns=["ISIN", "Datum", "Koers"])
        self.df_valutakoersen = pd.DataFrame(columns=["Valuta", "Datum", "Koers"])

    def voeg_obligatiekoers_toe(self, isin: str, datum: date, koers: float) -> None:
        self.df_obligatiekoersen.loc[len(self.df_obligatiekoersen)] = [isin, datum, koers]

    def voeg_valutakoers_toe(self, valuta: str, datum: date, koers: float) -> None:
        self.df_valutakoersen.loc[len(self.df_valutakoersen)] = [valuta, datum, koers]

    @staticmethod
    def _laatste_koers(df: pd.DataFrame, key_col: str, key: str, datum: date) -> float | None:
        df_sel = df[(df[key_col] == key) & (df["Datum"] <= datum)]
        if df_sel.empty:
            return None
        return float(df_sel.sort_values("Datum").iloc[-1]["Koers"])

    def waarde_op_datum(self, bond: PortfolioBond, peildatum: date) -> dict[str, float | date | str]:
        koers_obl = self._laatste_koers(self.df_obligatiekoersen, "ISIN", bond.isin, peildatum)
        koers_val = self._laatste_koers(self.df_valutakoersen, "Valuta", bond.valuta, peildatum) or 1.0
        if koers_obl is None:
            koers_obl = bond.aankoop_koers_pct

        marktwaarde = bond.nominale_waarde * koers_obl / 100.0
        accrued = bond.accrued_interest(peildatum)
        totale_waarde = (marktwaarde + accrued) / koers_val

        investering = bond.totale_investering()
        rendement = (totale_waarde - investering) / investering * 100 if investering else 0

        return {
            "Datum": peildatum,
            "ISIN": bond.isin,
            "Marktwaarde": round(marktwaarde, 2),
            "Opgelopen rente": round(accrued, 2),
            "Totale waarde €": round(totale_waarde, 2),
            "Rendement %": round(rendement, 2),
        }


def load_obligaties_csv(csv_path: str) -> list[dict]:
    df = pd.read_csv(csv_path, na_values=["", " "], keep_default_na=False)
    df = df.where(pd.notna(df), None)

    if "einddatum" in df.columns:
        df["einddatum"] = pd.to_datetime(df["einddatum"]).dt.date
    if "settlement_datum" in df.columns:
        df["settlement_datum"] = pd.to_datetime(df["settlement_datum"]).dt.date

    return df.to_dict(orient="records")


def resultaten_tabel(obligaties: Iterable[dict]) -> pd.DataFrame:
    rows = []
    for ob in obligaties:
        b = PortfolioBond(**ob)
        rows.append(
            {
                "ISIN": b.isin,
                "Naam": b.naam,
                "YTM (%)": round(b.ytm(), 2),
                "Valuta": b.valuta,
                "Valutakoers": b.valutakoers,
                "Settlement": b.settlement(),
                "Einddatum": b.einddatum,
                "Broker": b.broker,
                "Nominaal (V)": round(b.nominale_waarde, 0),
                "Aankoopkoers": round(b.aankoop_koers_pct, 2),
                "Leningbedrag (V)": round(b.leningbedrag(), 2),
                "Opgelopen rente (V)": round(b.accrued_interest(), 2),
                "Aankoopkosten (€)": round(b.bereken_aankoopkosten(), 2),
                "Totale investering (€)": round(b.totale_investering(), 2),
                "Jaarlijkse coupon (V)": round(b.jaarlijkse_coupon(), 2),
            }
        )
    return pd.DataFrame(rows)
