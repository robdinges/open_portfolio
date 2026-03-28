import pytest
from datetime import date
from open_portfolio.sample_data import create_realistic_dataset
from open_portfolio.reporting import PortfolioReporter


def test_realistic_dataset_creation():
    """Test that realistic dataset can be created with all components."""
    dataset = create_realistic_dataset()
    
    assert len(dataset['clients']) == 2
    assert len(dataset['portfolios']) == 3
    assert len(dataset['products']) == 27
    assert len(dataset['transactions']) >= 10
    
    # Verify clients
    assert dataset['clients'][0].name == "Alice Johnson"
    assert dataset['clients'][1].name == "Bob Smith"
    
    # Verify portfolios
    alice_eur = dataset['portfolios'][0]
    assert alice_eur.portfolio_id == 1
    assert alice_eur.default_currency == 'EUR'
    
    alice_usd = dataset['portfolios'][1]
    assert alice_usd.portfolio_id == 2
    assert alice_usd.default_currency == 'USD'
    
    bob_eur = dataset['portfolios'][2]
    assert bob_eur.portfolio_id == 3
    
    # Verify products
    assert any(p.description == "Apple Inc. (AAPL)" for p in dataset['products'])
    assert any(p.description == "EU Government Bond 2.5%" for p in dataset['products'])


def test_portfolio_reporter_summary(capsys):
    """Test that reporter can generate summary report."""
    dataset = create_realistic_dataset()
    reporter = PortfolioReporter(dataset['clients'])
    
    reporter.print_summary(valuation_date=date(2026, 3, 1))
    
    captured = capsys.readouterr()
    assert "PORTFOLIO SUMMARY REPORT" in captured.out
    assert "Alice Johnson" in captured.out
    assert "Bob Smith" in captured.out
    assert "01 March 2026" in captured.out


def test_portfolio_reporter_holdings(capsys):
    """Test that reporter can generate holdings report."""
    dataset = create_realistic_dataset()
    reporter = PortfolioReporter(dataset['clients'])
    
    reporter.print_detailed_holdings(valuation_date=date(2026, 3, 1))
    
    captured = capsys.readouterr()
    assert "DETAILED HOLDINGS REPORT" in captured.out
    assert "CASH ACCOUNTS:" in captured.out
    assert "SECURITIES:" in captured.out


def test_portfolio_reporter_transactions(capsys):
    """Test that reporter can generate transaction history."""
    dataset = create_realistic_dataset()
    reporter = PortfolioReporter(dataset['clients'])
    
    reporter.print_transaction_history()
    
    captured = capsys.readouterr()
    assert "TRANSACTION HISTORY" in captured.out
    assert "Portfolio" in captured.out


def test_portfolio_reporter_text_export():
    """Test that reporter can export to text."""
    dataset = create_realistic_dataset()
    reporter = PortfolioReporter(dataset['clients'])
    
    text_output = reporter.to_text(valuation_date=date(2026, 3, 1))
    
    assert "PORTFOLIO SUMMARY REPORT" in text_output
    assert "DETAILED HOLDINGS REPORT" in text_output
    assert "Alice Johnson" in text_output
