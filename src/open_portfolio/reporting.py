"""Comprehensive reporting module for portfolio analysis and visualization.

This module generates detailed reports on portfolio performance, holdings,
transactions, and returns. Reports can be printed to console or exported
as plain text.

Usage example::

    from open_portfolio.reporting import PortfolioReporter
    from open_portfolio.sample_data import create_realistic_dataset

    dataset = create_realistic_dataset()
    reporter = PortfolioReporter(dataset['clients'])
    
    reporter.print_all_reports(valuation_date=date.today())
"""

from datetime import date
from typing import List, Optional


class PortfolioReporter:

    """Generate comprehensive portfolio reports."""

    def __init__(self, clients):
        """Initialize reporter with clients."""
        self.clients = clients

    def to_markdown(self, valuation_date: Optional[date] = None) -> str:
        """Genereer een mooi uitgelijnd markdown rapport van alle portefeuilles."""
        if valuation_date is None:
            valuation_date = date.today()
        lines = []
        lines.append(f"# Portfolio Rapport\n")
        lines.append(f"_Valutatiedatum: {valuation_date.strftime('%d %B %Y')}_\n")

        # Samenvatting
        lines.append("## Samenvatting per client\n")
        for client in self.clients:
            lines.append(f"### {client.name} (ID: {client.client_id})\n")
            for portfolio in client.portfolios:
                try:
                    value = portfolio.calculate_holding_value(valuation_date)
                    cash_total = sum(acc.get_balance(valuation_date) for acc in portfolio.cash_accounts.values())
                    sec_value = value - cash_total
                    lines.append(f"- **Portfolio {portfolio.portfolio_id} ({portfolio.name})**: {portfolio.default_currency} {value:,.2f}  ")
                    lines.append(f"  - Cash: {portfolio.default_currency} {cash_total:,.2f}  ")
                    lines.append(f"  - Effecten: {portfolio.default_currency} {sec_value:,.2f}\n")
                except Exception as e:
                    lines.append(f"- Portfolio {portfolio.portfolio_id}: _Error: {e}_\n")

        # Holdings
        lines.append("## Gedetailleerde holdings\n")
        for client in self.clients:
            lines.append(f"### {client.name}\n")
            for portfolio in client.portfolios:
                lines.append(f"#### Portfolio {portfolio.portfolio_id} - {portfolio.name}\n")
                # Cash accounts
                lines.append("**Kasposities:**\n")
                lines.append("| Account ID | Valuta | Type | Saldo |")
                lines.append("|---|---|---|---:|")
                for (acct_id, curr, acc_type), account in portfolio.cash_accounts.items():
                    balance = account.get_balance(valuation_date)
                    lines.append(f"| {acct_id} | {curr} | {acc_type.name} | {balance:,.2f} |")
                lines.append("")
                # Securities
                if portfolio.securities_account.holdings:
                    lines.append("**Effecten:**\n")
                    lines.append("| Product ID | Omschrijving | Aantal | Prijs | Waarde |")
                    lines.append("|---|---|---:|---:|---:|")
                    for holding in portfolio.securities_account.holdings:
                        product = holding["product"]
                        amount = 0
                        for tx in product.transactions:
                            for mv in tx.security_movements:
                                if mv.transaction_date <= valuation_date:
                                    from .enums import MovementType
                                    if mv.movement_type == MovementType.SECURITY_BUY:
                                        amount += mv.amount_nominal
                                    elif mv.movement_type == MovementType.SECURITY_SELL:
                                        amount -= mv.amount_nominal
                        if amount > 0:
                            price = product.get_price(valuation_date) or 0.0
                            value = amount * price
                            lines.append(f"| {getattr(product, 'instrument_id', getattr(product, 'product_id', '-'))} | {product.description} | {amount:.0f} | {price:,.2f} | {value:,.2f} |")
                    lines.append("")
                else:
                    lines.append("_Geen effecten_\n")

        # Transacties
        lines.append("## Transactiegeschiedenis\n")
        for client in self.clients:
            lines.append(f"### {client.name}\n")
            for portfolio in client.portfolios:
                lines.append(f"#### Portfolio {portfolio.portfolio_id} - {portfolio.name}\n")
                lines.append("| Datum | Type | Product | Aantal | Prijs | Waarde |")
                lines.append("|---|---|---|---:|---:|---:|")
                transactions = portfolio.list_all_transactions()
                if not transactions:
                    lines.append("| _Geen transacties_ |  |  |  |  |  |")
                else:
                    for tx in transactions:
                        for sm in tx.get('security_movements', []):
                            product_desc = f"[{sm['product_id']}]"
                            amount = sm.get('amount_nominal', 0)
                            price = sm.get('price', 0)
                            value = amount * price
                            tx_type = sm.get('type', 'UNKNOWN')
                            lines.append(f"| {tx['transaction_date']} | {tx_type} | {product_desc} | {amount:.0f} | {price:,.2f} | {value:,.2f} |")
                lines.append("")

        return "\n".join(lines)
    
    def print_summary(self, valuation_date: Optional[date] = None):
        """Print brief summary of all portfolios."""
        if valuation_date is None:
            valuation_date = date.today()
        
        print("=" * 80)
        print("PORTFOLIO SUMMARY REPORT")
        print(f"Valuation Date: {valuation_date.strftime('%d %B %Y')}")
        print("=" * 80)
        print()
        
        total_portfolio_value = 0.0
        for client in self.clients:
            print(f"CLIENT: {client.name} (ID: {client.client_id})")
            print("-" * 80)
            for portfolio in client.portfolios:
                try:
                    value = portfolio.calculate_holding_value(valuation_date)
                    total_portfolio_value += value
                    cash_total = sum(
                        acc.get_balance(valuation_date) for acc in portfolio.cash_accounts.values()
                    )
                    sec_value = value - cash_total
                    print(
                        f"  Portfolio {portfolio.portfolio_id} ({portfolio.name}): "
                        f"{portfolio.default_currency} {value:,.2f} "
                        f"(Cash: {cash_total:,.2f}, Securities: {sec_value:,.2f})"
                    )
                except Exception as e:
                    print(f"  Portfolio {portfolio.portfolio_id}: Error - {e}")
            print()
        
        print("-" * 80)
        print(f"TOTAL PORTFOLIO VALUE: {total_portfolio_value:,.2f}")
        print("=" * 80)
        print()
    
    def print_detailed_holdings(self, valuation_date: Optional[date] = None):
        """Print detailed breakdown of all holdings by portfolio."""
        if valuation_date is None:
            valuation_date = date.today()
        
        print("=" * 80)
        print("DETAILED HOLDINGS REPORT")
        print(f"Valuation Date: {valuation_date.strftime('%d %B %Y')}")
        print("=" * 80)
        print()
        
        for client in self.clients:
            print(f"CLIENT: {client.name}")
            print("-" * 80)
            
            for portfolio in client.portfolios:
                print(f"\nPortfolio {portfolio.portfolio_id} - {portfolio.name}")
                print(f"Default Currency: {portfolio.default_currency}")
                print()
                
                # Cash accounts
                print("  CASH ACCOUNTS:")
                for (acct_id, curr, acc_type), account in portfolio.cash_accounts.items():
                    balance = account.get_balance(valuation_date)
                    print(f"    {acc_type.name:12} {curr:4} Account {acct_id}: {balance:>12,.2f}")
                
                # Securities
                if portfolio.securities_account.holdings:
                    print()
                    print("  SECURITIES:")
                    print(
                        f"    {'Product ID':12} {'Description':40} {'Amount':>10} "
                        f"{'Price':>10} {'Value':>15}"
                    )
                    print("    " + "-" * 76)
                    
                    for holding in portfolio.securities_account.holdings:
                        product = holding["product"]
                        amount = 0
                        for tx in product.transactions:
                            for mv in tx.security_movements:
                                if mv.transaction_date <= valuation_date:
                                    from .enums import MovementType
                                    if mv.movement_type == MovementType.SECURITY_BUY:
                                        amount += mv.amount_nominal
                                    elif mv.movement_type == MovementType.SECURITY_SELL:
                                        amount -= mv.amount_nominal
                        
                        if amount > 0:
                            price = product.get_price(valuation_date) or 0.0
                            value = amount * price
                            print(
                                f"    {product.instrument_id:12} {product.description:40} "
                                f"{amount:>10.0f} {price:>10,.2f} {value:>15,.2f}"
                            )
                else:
                    print("  SECURITIES: None")
                
                print()
        
        print("=" * 80)
        print()
    
    def print_transaction_history(self):
        """Print transaction history for all portfolios."""
        print("=" * 80)
        print("TRANSACTION HISTORY")
        print("=" * 80)
        print()
        
        for client in self.clients:
            print(f"CLIENT: {client.name}")
            print("-" * 80)
            
            for portfolio in client.portfolios:
                print(f"\nPortfolio {portfolio.portfolio_id} - {portfolio.name}")
                print(
                    f"{'Date':12} {'Type':8} {'Product':40} "
                    f"{'Amount':>10} {'Price':>10} {'Value':>15}"
                )
                print("-" * 95)
                
                transactions = portfolio.list_all_transactions()
                if not transactions:
                    print("  No transactions recorded.")
                else:
                    for tx in transactions:
                        for sm in tx.get('security_movements', []):
                            product_desc = f"[{sm['product_id']}]"
                            amount = sm.get('amount_nominal', 0)
                            price = sm.get('price', 0)
                            value = amount * price
                            tx_type = sm.get('type', 'UNKNOWN')
                            print(
                                f"{tx['transaction_date']}  {tx_type:8} {product_desc:40} "
                                f"{amount:>10.0f} {price:>10,.2f} {value:>15,.2f}"
                            )
                
                print()
        
        print("=" * 80)
        print()
    
    def print_cash_position(self, valuation_date: Optional[date] = None):
        """Print cash position summary for all portfolios."""
        if valuation_date is None:
            valuation_date = date.today()
        
        print("=" * 80)
        print("CASH POSITION REPORT")
        print(f"Valuation Date: {valuation_date.strftime('%d %B %Y')}")
        print("=" * 80)
        print()
        
        for client in self.clients:
            print(f"CLIENT: {client.name}")
            print("-" * 80)
            
            for portfolio in client.portfolios:
                print(f"\nPortfolio {portfolio.portfolio_id} - {portfolio.name}")
                
                total_by_currency = {}
                for (acct_id, curr, acc_type), account in portfolio.cash_accounts.items():
                    balance = account.get_balance(valuation_date)
                    if curr not in total_by_currency:
                        total_by_currency[curr] = 0.0
                    total_by_currency[curr] += balance
                    print(f"  {acc_type.name:12} {curr:4}: {balance:>12,.2f}")
                
                print(f"\n  Totals by currency:")
                for curr, total in sorted(total_by_currency.items()):
                    print(f"    {curr}: {total:>12,.2f}")
                print()
        
        print("=" * 80)
        print()
    
    def print_all_reports(self, valuation_date: Optional[date] = None):
        """Print all available reports."""
        if valuation_date is None:
            valuation_date = date.today()
        
        self.print_summary(valuation_date)
        self.print_cash_position(valuation_date)
        self.print_detailed_holdings(valuation_date)
        self.print_transaction_history()
    
    def to_text(self, valuation_date: Optional[date] = None) -> str:
        """Generate all reports as a single text string."""
        if valuation_date is None:
            valuation_date = date.today()
        
        import io
        import sys
        
        # Redirect stdout to capture print output
        old_stdout = sys.stdout
        sys.stdout = buffer = io.StringIO()
        
        try:
            self.print_all_reports(valuation_date)
            return buffer.getvalue()
        finally:
            sys.stdout = old_stdout


if __name__ == "__main__":
    from .sample_data import create_realistic_dataset
    
    dataset = create_realistic_dataset()
    reporter = PortfolioReporter(dataset['clients'])
    reporter.print_all_reports(valuation_date=date(2026, 3, 1))
