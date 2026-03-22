"""Very simple GUI sketches for the portfolio library.

This module contains a minimal Tkinter application that demonstrates how the
core library could be used from a graphical interface.  It is intentionally
lightweight; a production application would likely use a framework such as
PyQt, Kivy, Flask/React or Streamlit.

The key screens are:

* **Transaction entry** – choose a portfolio, pick a product, enter amount/price
  and execute a BUY/SELL/DEPOSIT.
* **Portfolio overview** – show cash account balances and security holdings.
* **Transaction history** – display all executed transactions in a table.

Only skeletal widgets are created; the logic for filling combo boxes and
hooking up actions should be written by the end user.
"""

import sys
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date

from .product_collection import ProductCollection
from .clients import Client
from .transactions import TransactionManager
from .enums import TransactionTemplate, AccountType, PaymentFrequency
from .products import Stock, Bond
from .prices import CurrencyPrices


class PortfolioApp(tk.Tk):
    def __init__(self, client):
        super().__init__()
        self.title("OpenPortfolio Manager")
        self.geometry("800x600")
        self.client = client
        self.product_collection = ProductCollection()
        self.currency_prices = CurrencyPrices()
        self.tx_manager = TransactionManager()

        # main notebook pages
        nb = ttk.Notebook(self)
        self.tx_frame = ttk.Frame(nb)
        self.overview_frame = ttk.Frame(nb)
        nb.add(self.tx_frame, text="Transactions")
        nb.add(self.overview_frame, text="Overview")
        nb.pack(fill="both", expand=True)

        self._build_transaction_page()
        self._build_overview_page()

    def _build_transaction_page(self):
        # basic form fields
        row = 0
        ttk.Label(self.tx_frame, text="Portfolio:").grid(column=0, row=row, sticky="w")
        self.portfolio_combo = ttk.Combobox(self.tx_frame, values=[p.portfolio_id for p in self.client.portfolios])
        self.portfolio_combo.grid(column=1, row=row)
        row += 1

        ttk.Label(self.tx_frame, text="Type:").grid(column=0, row=row, sticky="w")
        self.type_combo = ttk.Combobox(self.tx_frame, values=[t.name for t in TransactionTemplate])
        self.type_combo.grid(column=1, row=row)
        row += 1

        ttk.Label(self.tx_frame, text="Product ID:").grid(column=0, row=row, sticky="w")
        self.product_combo = ttk.Combobox(self.tx_frame, values=[p.instrument_id for p in self.product_collection.products.values()])
        self.product_combo.grid(column=1, row=row)
        ttk.Button(self.tx_frame, text="Refresh products", command=self.refresh_products).grid(column=2, row=row)
        row += 1

        ttk.Label(self.tx_frame, text="Amount:").grid(column=0, row=row, sticky="w")
        self.amount_entry = ttk.Entry(self.tx_frame)
        self.amount_entry.grid(column=1, row=row)
        row += 1

        ttk.Label(self.tx_frame, text="Price:").grid(column=0, row=row, sticky="w")
        self.price_entry = ttk.Entry(self.tx_frame)
        self.price_entry.grid(column=1, row=row)
        row += 1

        ttk.Button(self.tx_frame, text="Execute", command=self._on_execute).grid(column=0, row=row, columnspan=2)

    def _build_overview_page(self):
        self.accounts_text = tk.Text(self.overview_frame, height=10)
        self.accounts_text.pack(fill="x")
        self.holdings_text = tk.Text(self.overview_frame, height=10)
        self.holdings_text.pack(fill="x")
        ttk.Button(self.overview_frame, text="Refresh", command=self._refresh_overview).pack()

    def _on_execute(self):
        try:
            portfolio_id = int(self.portfolio_combo.get())
            portfolio = next(p for p in self.client.portfolios if p.portfolio_id == portfolio_id)
            template = TransactionTemplate[self.type_combo.get()]
            prod_val = self.product_combo.get()
            product_id = int(prod_val) if prod_val else None
            amount = float(self.amount_entry.get())
            price = float(self.price_entry.get())
            self.tx_manager.create_and_execute_transaction(
                transaction_date=None,  # use today
                portfolio_id=portfolio_id,
                template=template,
                portfolio=portfolio,
                product_collection=self.product_collection,
                currency_prices=self.currency_prices,
                product_id=product_id,
                amount=amount,
                price=price,
            )
            messagebox.showinfo("Success", "Transaction executed")
            self._refresh_overview()
        except Exception as ex:
            messagebox.showerror("Error", str(ex))

    def _refresh_overview(self):
        self.accounts_text.delete(1.0, tk.END)
        for p in self.client.portfolios:
            self.accounts_text.insert(tk.END, f"Portfolio {p.portfolio_id} ({p.name})\n")
            for (acct_id, curr, acc_type), acc in p.cash_accounts.items():
                self.accounts_text.insert(tk.END, f"  Account {acct_id} {acc_type.name} {curr}: {acc.balance}\n")
            self.accounts_text.insert(tk.END, "\n")
        self.holdings_text.delete(1.0, tk.END)
        for p in self.client.portfolios:
            if not p.securities_account.holdings:
                self.holdings_text.insert(tk.END, f"Portfolio {p.portfolio_id}: no holdings\n")
            else:
                for h in p.securities_account.holdings:
                    prod = h.get("product")
                    amount = h.get("amount", 0)
                    self.holdings_text.insert(tk.END, f"  Product {prod.instrument_id} {prod.description}: {amount}\n")

    def refresh_products(self):
        # simple helper to repopulate product combobox values
        vals = [prod.instrument_id for prod in self.product_collection.products.values()]
        self.product_combo['values'] = vals
        if vals:
            self.product_combo.set(vals[0])


if __name__ == "__main__":
    # quick demo with optional headless mode for diagnostics
    import argparse

    parser = argparse.ArgumentParser(prog="open_portfolio.gui", description="Run the demo GUI (or headless test)")
    parser.add_argument("--headless", "--no-gui", dest="headless", action="store_true", help="Create the app but do not start the main loop (useful for testing)")
    parser.add_argument("--demo", dest="demo", action="store_true", help="Populate demo products, accounts and currencies")
    args = parser.parse_args()

    c = Client(1, "Demo")
    # create a default portfolio so the combobox is populated
    try:
        pt = c.add_portfolio(1)
    except Exception:
        pt = next((p for p in c.portfolios if p.portfolio_id == 1), None)

    app = PortfolioApp(c)

    if args.demo:
        # populate demo data in the app's product collection and currency prices
        # add demo products (if not already present)
        try:
            app.product_collection.add_product(Stock(product_id=1001, description='Demo USD Stock', minimum_purchase_value=1, smallest_trading_unit=1, issue_currency='USD'))
        except Exception:
            pass
        try:
            app.product_collection.add_product(
                Bond(
                    instrument_id=1002,
                    description='Demo EUR Bond',
                    minimum_purchase_value=1000,
                    smallest_trading_unit=1,
                    issue_currency='EUR',
                    start_date=date(2024, 1, 1),
                    maturity_date=date(2026, 1, 1),
                    interest_rate=0.03,
                    interest_payment_frequency=PaymentFrequency.END_DATE,
                )
            )
        except Exception:
            pass

        # demo currency price
        try:
            app.currency_prices.add_price('USD', date.today(), 1.10)
        except Exception:
            pass

        # refresh product combobox
        try:
            app.refresh_products()
        except Exception:
            pass

    if args.headless:
        # perform a single update cycle and destroy; this won't block
        print("Running in headless mode: creating GUI and exiting immediately")
        try:
            app.update()
        except Exception as e:
            print("GUI update failed:", e)
            raise
        finally:
            try:
                app.destroy()
            except Exception:
                pass
        sys.exit(0)

    # normal blocking GUI start
    app.mainloop()
