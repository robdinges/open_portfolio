# REQ-04 — Berekeningen, business rules en validaties

Datum: 2026-04-06
Bron: `REQUIREMENTS.md` (FR-13 t/m FR-24), `ORDER_ENTRY.md`, `ORDER_ENTRY_REQUIREMENTS_STRUCTURED.md`, `ORDER_ENTRY_BACKLOG.md`

---

## 1. Transactieberekeningen

### 1.1 Brutobedrag

| Regel | Beschrijving | Status |
|---|---|---|
| BR-001 | Brutobedrag = hoeveelheid × prijsbasis. | [IMPL] |
| BR-002 | Obligaties: prijsbasis = nominaal × koers% / 100. Voorbeeld: nominaal 200.000 × 101,25% = 202.500,00. | [IMPL] |
| BR-003 | Aandelen: prijsbasis = aantal × stukprijs. | [IMPL] |

### 1.2 Transactiekosten

| Regel | Beschrijving | Status |
|---|---|---|
| BR-010 | Standaardkostenmethode: 0,1% van de transactiewaarde in afrekenmuntvaluta. | [IMPL] |
| BR-011 | Teken van kosten volgt transactierichting (negatief bij aankoop, positief bij verkoop). | [IMPL] |
| BR-012 | [GAP] Uitgebreid kostenmodel: percentage + vast + venue-specifiek (OE-GAP-002/006). | [GAP] |

### 1.3 Opgelopen rente

| Regel | Beschrijving | Status |
|---|---|---|
| BR-020 | Opgelopen rente geldt alleen voor obligaties. Overige instrumenten: 0,00. | [IMPL] |
| BR-021 | Berekening op basis van dag-telconventie van het instrument: ACT/ACT, 30E/360. | [IMPL] |
| BR-022 | Renteperiode: van laatste coupondatum (inclusief) tot transactiedatum (exclusief). | [IMPL] |
| BR-023 | Zero-coupon obligaties genereren geen opgelopen rente. | [SPEC] |
| BR-024 | Negatieve opgelopen rente mag niet voorkomen; ongeldige datumcombinatie blokkeert order. | [SPEC] |
| BR-025 | [GAP] Berekening op settlementdatum (T+n) i.p.v. transactiedatum (OE-GAP-007). | [GAP] |
| BR-026 | [GAP] Negatieve rente bij ex-couponperiode: waarschuwing tonen zonder blokkade (OE-GAP-008). | [GAP] |

### 1.4 Nettobedrag

| Regel | Beschrijving | Status |
|---|---|---|
| BR-030 | Aankoop: netto = bruto + kosten + opgelopen rente. | [IMPL] |
| BR-031 | Verkoop: netto = bruto − kosten ± opgelopen rente (volgens marktconventie). | [IMPL] |
| BR-032 | Afronding: half-up naar valutaprecisie (2 decimalen). | [SPEC] |

### 1.5 Wisselkoers

| Regel | Beschrijving | Status |
|---|---|---|
| BR-040 | Als afrekenmuntvaluta verschilt van instrumentvaluta: FX-conversie toepassen. | [IMPL] |
| BR-041 | Gebruik meest recente FX-koers op of vóór transactiedatum. | [IMPL] |
| BR-042 | Als directe koers ontbreekt: gebruik reverse FX. | [IMPL] |
| BR-043 | Bij gelijke valuta: wisselkoers = 1,0 (geen conversie). | [IMPL] |

### 1.6 Koersbepaling

| Regel | Beschrijving | Status |
|---|---|---|
| BR-050 | Market-order: gebruik meest recente instrumentkoers op of vóór transactiedatum. | [IMPL] |
| BR-051 | Limit-order: gebruik de door de gebruiker ingevoerde limietprijs. | [IMPL] |
| BR-052 | [GAP] Intraday prijsversheid: market order vereist koers binnen configureerbare window (OE-GAP-003). | [GAP] |

## 2. Formuleberekening reconciliatie (broker-vergelijking)

| Regel | Beschrijving | Status |
|---|---|---|
| BR-060 | Aankoop/Verkoop: `((nominaal × koers × FX) + opgelopen rente) + kosten`. | [SPEC] |
| BR-061 | Coupon: `nominaal`. | [SPEC] |
| BR-062 | Aflossing: `nominaal × koers × FX` (zonder kosten). | [SPEC] |
| BR-063 | Verschil = formulebedrag − brokerbedrag. | [SPEC] |

## 3. Analyse: Verkoop Nu

| Regel | Beschrijving | Status |
|---|---|---|
| BR-070 | Verkoopwaarde inclusief meeverkochte rente en 0,1% kosten. | [SPEC] |
| BR-071 | Bedragvelden tonen alleen bedragen, geen tekstuele toelichting. | [SPEC] |

## 4. Analyse: SELL vs HOLD

| Regel | Beschrijving | Status |
|---|---|---|
| BR-080 | Vergelijking gebruikt alleen cashflows vanaf vandaag. Historische coupons alleen als context. | [SPEC] |
| BR-081 | Alle toekomstige cashflows contant gemaakt naar vandaag met configureerbare discontovoet. | [SPEC] |
| BR-082 | SELL-scenario voor drie prijsaannames: huidige − 0,5%, huidige, huidige + 0,5%. | [SPEC] |
| BR-083 | Verkoopopbrengst = clean price + opgelopen rente, geconverteerd naar EUR via actuele FX. | [SPEC] |
| BR-084 | HOLD-scenario: alle resterende coupons + aflossing op 100% nominaal op einddatum. | [SPEC] |
| BR-085 | Cashflowtabel toont per regel: datum, bedrag, discount factor, contante waarde. | [SPEC] |

## 5. Validaties

### 5.1 Ordervalidaties

| Regel | Beschrijving | Status |
|---|---|---|
| VL-001 | Verplichte velden: portefeuille, instrument, transactiesoort, ordertype, hoeveelheid, afrekenmuntrekening. Limietprijs verplicht bij LIMIT-orders. | [IMPL] |
| VL-002 | Hoeveelheid moet strikt groter dan nul zijn. | [IMPL] |
| VL-003 | Hoeveelheid moet een veelvoud zijn van de handelseenheid (`smallest_trading_unit`). | [IMPL] |
| VL-004 | Hoeveelheid moet voldoen aan minimale ordergrootte (`minimum_purchase_value`). | [IMPL] |
| VL-005 | Market-order mag geen limietprijs bevatten; limit-order moet een limietprijs bevatten. | [SPEC] |
| VL-006 | Instrument moet actief zijn op de transactiedatum. | [IMPL] |

### 5.2 Positie- en saldobewaking

| Regel | Beschrijving | Status |
|---|---|---|
| VL-010 | Verkoop: beschikbare hoeveelheid mag niet worden overschreden. | [IMPL] |
| VL-011 | Aankoop: beschikbaar saldo op afrekenmuntrekening moet voldoende zijn voor nettobedrag. | [IMPL] |
| VL-012 | Debetsaldo niet toegestaan na boeking. | [IMPL] |
| VL-013 | [GAP] Geavanceerde risicolimieten: concentratie, dagnotional, traderlimieten (OE-GAP-001). | [GAP] |

### 5.3 Rekeningvalidatie

| Regel | Beschrijving | Status |
|---|---|---|
| VL-020 | Afrekenrekening moet in dezelfde portefeuille en bij dezelfde client horen. | [IMPL] |
| VL-021 | Afrekenrekening beperkt tot instrumentvaluta of portefeuillebasisvaluta. | [IMPL] |
| VL-022 | Bij gelijke valuta: rekening automatisch geselecteerd, niet wijzigbaar. | [IMPL] |
| VL-023 | Bij afwijkende valuta: keuze uit instrumentvaluta- of portefeuillevalutarekening (indien beide bestaan). | [IMPL] |
| VL-024 | Geen rekening beschikbaar: order geblokkeerd met melding. | [SPEC] |

### 5.4 Invoervalidatie

| Regel | Beschrijving | Status |
|---|---|---|
| VL-030 | Numerieke velden accepteren komma en punt als decimaalteken. | [IMPL] |
| VL-031 | Positieve getallen vereist voor hoeveelheid en prijs. | [IMPL] |
| VL-032 | Ongeldige invoer levert een duidelijke, Nederlandstalige foutmelding. | [IMPL] |

## 6. Transactietemplates

| Template | Beschrijving | Status |
|---|---|---|
| BR-100 | BUY: effectenboeking + kasafboeking + kosten + (opgelopen rente bij bonds). | [IMPL] |
| BR-101 | SELL: effectenafboeking + kascreditering + kosten + (opgelopen rente bij bonds). | [IMPL] |
| BR-102 | DEPOSIT: storting op kasrekening. | [IMPL] |
| BR-103 | DIVIDEND: creditering op kasrekening. | [IMPL] |
| BR-104 | Aflossing: verkoop op 100% zonder kosten. | [SPEC] |
| BR-105 | Coupon betaling: altijd in basisvaluta EUR. | [SPEC] |

## 7. Idempotentie en deduplicatie

| Regel | Beschrijving | Status |
|---|---|---|
| BR-110 | Herhaald importeren van hetzelfde bestand leidt niet tot dubbele boekingen. | [SPEC] |
| BR-111 | Deduplicatie op unieke transactiesleutel (`tx_key`), bij voorkeur op `Referentie`. | [SPEC] |
| BR-112 | Bestaande transactie: melden + overslaan (geen dubbele boeking). | [SPEC] |
