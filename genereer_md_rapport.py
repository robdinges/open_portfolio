from open_portfolio.reporting import PortfolioReporter
from open_portfolio.sample_data import create_realistic_dataset
from datetime import date

dataset = create_realistic_dataset()
reporter = PortfolioReporter(dataset['clients'])

md_report = reporter.to_markdown(valuation_date=date.today())
with open('portfolio_report.md', 'w') as f:
    f.write(md_report)

print("Markdown rapport gegenereerd op basis van de JSON-data.")
