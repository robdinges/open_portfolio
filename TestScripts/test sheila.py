import pandas as pd

# Define the structure of the financial overview table with categories and descriptions
data = {
    "Categorie": [
        "Inkomsten", "Prepensioen", "AOW uit Curaçao", "Zorgtoeslag", "Huurtoeslag", 
        "Vaste Uitgaven", "Huur incl. servicekosten", "Gas en Elektra", "Water", "Internet en TV", 
        "Zorgverzekering", "Gemeentelijke belastingen", "Telefoon", "Verzekeringen", "Autoverzekering", 
        "Inboedelverzekering", "Aansprakelijkheidsverzekering", "Uitvaartverzekering",
        "Reserveringen", "NS Abonnement", "ANWB (wegenwacht)", "Auto-onderhoud", "Onderhoud huis", "Vervangingen",
        "Variabele Uitgaven", "Boodschappen", "Benzine", "Openbaar vervoer", "Kleding en verzorging", "Vrijetijdsbesteding",
        "Resultaat"
    ],
    "Omschrijving": [
        "", "", "", "", "",
        "", "", "", "", "",
        "", "", "", "", "",
        "", "", "",
        "", "", "", "", "", "",
        "", "", "", "", "", "",
        ""
    ],
    "Maandbedrag (€)": [
        None, "=SUM(B3:B6)", None, None, None,
        None, None, None, None, None,
        None, None, None, None, None,
        None, None, None,
        None, None, None, None, None, None,
        None, None, None, None, None, None,
        "=B2-SUM(B7:B13,B15:B18,B20:B30)"
    ],
    "Notities": [
        "Totaal inkomen", "Maandelijks bedrag", "Maandelijks bedrag", "Maandelijks bedrag", "Maandelijks bedrag",
        "Totaal vaste uitgaven", "Maandelijks bedrag", "Maandelijks bedrag", "Maandelijks bedrag", "Maandelijks bedrag",
        "Zorgtoeslag in rekening gebracht", "Inclusief alle lokale heffingen", "Maandelijks bedrag", "Totale verzekeringskosten", "Maandelijks bedrag",
        "Maandelijks bedrag", "Maandelijks bedrag", "Maandelijks bedrag",
        "Totaal gereserveerd per maand (1/12 jaarlijkse kosten)", "Jaarlijkse kosten gedeeld door 12", "Jaarlijkse kosten gedeeld door 12", "Jaarlijkse kosten gedeeld door 12", "Jaarlijkse kosten gedeeld door 12", "Jaarlijkse kosten gedeeld door 12",
        "Totaal variabele uitgaven", "Maandelijks bedrag", "Maandelijks bedrag", "Maandelijks bedrag", "Maandelijks bedrag", "Maandelijks bedrag",
        "Inkomsten minus uitgaven en reserveringen"
    ]
}

# Create a DataFrame
df = pd.DataFrame(data)

# Set a blank Excel writer and the file path
file_path = 'Financieel_Overzicht.xlsx'
writer = pd.ExcelWriter(file_path, engine='xlsxwriter')

# Write DataFrame to Excel
df.to_excel(writer, sheet_name='Overzicht', index=False)

# Get the xlsxwriter workbook and worksheet objects.
workbook  = writer.book
worksheet = writer.sheets['Overzicht']

# Format cells
format1 = workbook.add_format({'num_format': '#,##0.00 €', 'align': 'right'})
worksheet.set_column('B:B', 20, format1)  # Set format for monetary values
worksheet.set_column('A:A', 25)
worksheet.set_column('C:C', 20)
worksheet.set_column('D:D', 50)

# Save the Excel file
writer.close()

file_path


