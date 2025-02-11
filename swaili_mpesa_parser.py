import re
from datetime import datetime
from typing import Dict, Optional

class SwahiliMPESAParser:
    def __init__(self):
        # Base confirmation pattern
        self.base_pattern = r"(?P<transaction_id>[A-Z0-9]{10})\s+Imethibitishwa\.?\s*"
        
        # Transaction patterns with specific Swahili formats
        self.transaction_patterns = {
            # Kutuma pesa kwa mtu
            'KUTUMA': (
                r"Ksh(?P<kutuma_amount>[\d,.]+)\s"
                r"imetumwa\skwa\s"
                r"(?P<kutuma_recipient>[^0-9]+?)\s"
                r"(?P<kutuma_phone>\d{10})\s"
                r"(?:tarehe|siku)\s"
                r"(?P<kutuma_date>\d{1,2}/\d{1,2}/\d{2})\s"
                r"saa\s(?P<kutuma_time>\d{1,2}:\d{2}\s*[AP]M)"
            ),
            
            # Kupokea pesa
            'KUPOKEA': (
                r"Umepokea\sKsh(?P<kupokea_amount>[\d,.]+)\s"
                r"kutoka\s"
                r"(?P<kupokea_sender>[^0-9]+?)\s"
                r"(?P<kupokea_phone>\d{10})\s"
                r"mnamo\s"
                r"(?P<kupokea_date>\d{1,2}/\d{1,2}/\d{2})\s"
                r"saa\s(?P<kupokea_time>\d{1,2}:\d{2}\s*[AP]M)"
            ),
            
            # Angalia Salio
            'SALIO': (
                r"Baki\syako\sni:\s"
                r"Akaunti\sya\sM-PESA\s:\s"
                r"Ksh(?P<salio_amount>[\d,.]+)\s"
                r"(?:Tarehe|tarehe)\s"
                r"(?P<salio_date>\d{1,2}/\d{1,2}/\d{2})\s"
                r"saa\s(?P<salio_time>\d{1,2}:\d{2}\s*[AP]M)"
            ),
            
            # Kulipa Till
            'KULIPA_TILL': (
                r"Umelipa\sKsh(?P<kulipa_amount>[\d,.]+)\s"
                r"kwa\s(?P<kulipa_merchant>[^0-9]+?)\s"
                r"(?P<kulipa_date>\d{1,2}/\d{1,2}/\d{2})\s"
                r"(?P<kulipa_time>\d{1,2}:\d{2}\s*[AP]M)"
            ),
            
            # Data Bundles
            'DATA': (
                r"Ksh(?P<data_amount>[\d,.]+)\s"
                r"zimetumwa\skwa\sSAFARICOM\sDATA\sBUNDLES"
                r"(?:\skwa\sakaunti\sSAFARICOM\sDATA\sBUNDLES)?\s"
                r"mnamo\s"
                r"(?P<data_date>\d{1,2}/\d{1,2}/\d{2})\s"
                r"saa\s(?P<data_time>\d{1,2}:\d{2}\s*[AP]M)"
            ),
            
            # Kununua Mjazo (Airtime)
            'MJAZO': (
                r"Umenunua\sKsh(?P<mjazo_amount>[\d,.]+)\s"
                r"ya\smjazo\s"
                r"(?:siku|tarehe)\s"
                r"(?P<mjazo_date>\d{1,2}/\d{1,2}/\d{2})\s"
                r"saa\s(?P<mjazo_time>\d{1,2}:\d{2}\s*[AP]M)"
            ),
            
            # Equity Paybill
            'PAYBILL': (
                r"Ksh(?P<paybill_amount>[\d,.]+)\s"
                r"imetumwa\skwa\s(?P<paybill_name>[^k]+?)\s"
                r"kwa\sakaunti\snambari\s(?P<paybill_account>\d+)"
            ),
            
            # Kupokea kutoka Equity
            'KUPOKEA_BANK': (
                r"Umepokea\sKsh(?P<kupokea_bank_amount>[\d,.]+)\s"
                r"kutoka\s(?P<kupokea_bank_name>[^0-9]+?)\s"
                r"(?P<kupokea_bank_account>\d+)\s"
                r"mnamo\s"
                r"(?P<kupokea_bank_date>\d{1,2}/\d{1,2}/\d{2})\s"
                r"saa\s(?P<kupokea_bank_time>\d{1,2}:\d{2}\s*[AP]M)"
            ),
            
            # Sending money to Pochi la Biashara
            'POCHI_LA_BIASHARA': (
                r"Ksh(?P<pochi_amount>[\d,.]+)\s"
                r"imetumwa\skwa\s"
                r"(?P<pochi_recipient>[^0-9]+?)\s"
                r"(?:tarehe|siku)\s"
                r"(?P<pochi_date>\d{1,2}/\d{1,2}/\d{2})\s"
                r"saa\s(?P<pochi_time>\d{1,2}:\d{2}\s*[AP]M)"
            )
        }
        
        # Additional information patterns
        self.additional_patterns = {
            'mpesa_balance': r"Baki\s(?:yako|mpya)(?:\sya|\smpya\skatika|\skatika)\sM-PESA\sni\sKsh(?P<mpesa_balance>[\d,.]+)",
            'transaction_cost': r"Gharama\sya\s(?:kutuma|kununua|matumizi|kulipa)\sni\sKsh(?P<transaction_cost>[\d,.]+)",
            'daily_limit': r"Kiwango\scha\sPesa\sunachoweza\skutuma\skwa\ssiku\sni\s(?P<daily_limit>[\d,.]+)"
        }
        
        # Failed transaction patterns
        self.failed_pattern = re.compile(
            r"(?:"
            r"Hakuna\spesa\sza\skutosha|"
            r"Imefeli|"
            r"Umekataa\skuidhinisha\samali|"
            r"Huduma\shi\shaipatikani"
            r")"
        )
        
        # Compile patterns
        self.compile_patterns()

    def compile_patterns(self):
        """Compile all patterns into the main regex pattern"""
        # Combine transaction patterns
        transaction_part = '|'.join(
            f"(?P<{tx_type}>{pattern})"
            for tx_type, pattern in self.transaction_patterns.items()
        )
        
        # Add optional additional information patterns
        additional_part = ''.join(
            f"(?:.*?{pattern})?"
            for pattern in self.additional_patterns.values()
        )
        
        # Complete pattern
        complete_pattern = (
            f"(?:{self.base_pattern})?"  # Made base pattern optional for failed transactions
            f"({transaction_part})"
            f"{additional_part}"
        )
        
        self.pattern = re.compile(complete_pattern, re.IGNORECASE | re.DOTALL)

    def clean_amount(self, amount_str: str) -> float:
        """Clean amount string and convert to float."""
        if not amount_str:
            return 0.0
        cleaned = amount_str.replace(',', '').replace(' ', '').strip().rstrip('.')
        return float(cleaned)

    def parse_message(self, message: str) -> Dict[str, any]:
        """Parse a Swahili M-PESA message and extract details."""
        if not isinstance(message, str):
            return {"error": "Ujumbe lazima uwe maandishi"}
            
        # Check for failed transaction
        failed_match = self.failed_pattern.search(message)
        if failed_match:
            return {
                "hali": "IMESHINDIKANA",
                "sababu": failed_match.group(0),
                "ujumbe_asili": message
            }
        
        # Match message against pattern
        match = self.pattern.search(message)
        if not match:
            return {"error": "Muundo wa ujumbe hautambuliwi"}
            
        result = {k: v for k, v in match.groupdict().items() if v is not None}
        
        # Clean up values
        for key in result:
            if isinstance(result[key], str):
                result[key] = result[key].strip()
        
        # Set transaction status
        result['hali'] = 'IMEFAULU'
        
        # Determine transaction type and clean amount
        for tx_type in self.transaction_patterns.keys():
            if result.get(tx_type):
                result['aina_ya_muamala'] = tx_type
                amount_key = f"{tx_type.lower()}_amount"
                if amount_key in result:
                    result['kiasi'] = self.clean_amount(result[amount_key])
                    del result[amount_key]
                break
        
        # Clean numeric fields
        numeric_fields = {
            'mpesa_balance': 'salio_la_mpesa',
            'transaction_cost': 'gharama',
            'daily_limit': 'kikomo_cha_siku'
        }
        
        for eng_key, swa_key in numeric_fields.items():
            if eng_key in result:
                result[swa_key] = self.clean_amount(result[eng_key])
                del result[eng_key]
        
        # Parse date and time if present
        if 'date' in result and 'time' in result:
            try:
                datetime_str = f"{result['date']} {result['time']}"
                result['tarehe_na_saa'] = datetime.strptime(datetime_str, '%d/%m/%y %I:%M %p')
                del result['date']
                del result['time']
            except ValueError:
                pass
        
        return result

def test_parser():
    parser = SwahiliMPESAParser()
    
    # Test messages
    test_messages = [
        "TAD72CZ6J3 Imethibitishwa. Baki yako ni: Akaunti ya M-PESA : Ksh263.47 Tarehe 13/1/25 saa 5:36 PM. Gharama ya matumizi ni Ksh0.00.",
        "TAF5BV0XRN Umenunua Ksh5.00 ya mjazo siku 15/1/25 saa 8:44 PM.Baki mpya ya M-PESA ni Ksh38.47.",
        "Hakuna pesa za kutosha katika akaunti yako ya M-PESA kuweza kutuma Ksh3,251.00.",
        "TAE16URS8R Imethibitishwa Ksh10.00 imetumwa kwa MERCILINE  OSEWE tarehe 14/1/25 saa 6:34 PM. Baki yako ya M-PESA ni Ksh113.47. Gharama ya kutuma ni Ksh0.00. Kiwango cha Pesa unachoweza kutuma kwa siku ni 499,870.00.",

         "TAE86U0FMU Imethibitishwa Ksh50.00 imetumwa kwa ELIZABETH  ONYANGO tarehe 14/1/25 saa 6:30 PM. Baki yako ya M-PESA ni Ksh123.47. Gharama ya kutuma ni Ksh0.00. Kiwango cha Pesa unachoweza kutuma kwa siku ni 499,880.00.",

        "TAE55NG2RH Imethibitishwa Ksh50.00 imetumwa kwa ELIZABETH  ONYANGO tarehe 14/1/25 saa 1:48 PM. Baki yako ya M-PESA ni Ksh193.47. Gharama ya kutuma ni Ksh0.00. Kiwango cha Pesa unachoweza kutuma kwa siku ni 499,950.00.",


        "TAE46D879G Imethibitishwa. Umelipa Ksh20.00 kwa JUDITH ATIENO WERE 14/1/25 4:53 PM.Baki yako mpya katika M-PESA ni Ksh173.47. Gharama ya kununua ni Ksh0.00. Kiwango cha Pesa unachoweza kutuma kwa siku ni 499,930.00.Huduma za M-PESA sasa zinapatikana kwa *334#.",



"TAD43EZZ3O Imethibitishwa Ksh20.00 imetumwa kwa Eliud  Otieno 0792469173 tarehe 13/1/25 saa 8:37 PM. Baki yako ya M-PESA ni Ksh243.47. Gharama ya kutuma ni Ksh0.00.Kiwango cha Pesa unachoweza kutuma kwa siku ni 499,929.00. SAFARICOM HUPIGA NA 0722000000 PEKEE. Kurudisha hizi Pesa,Tuma ujumbe huu kwa 456.",

"Umekataa kuidhinisha amali ya KSH20.00. Usipositisha kwa mara 5, hautakubaliwa kutumia huduma ya M-PESA HAKIKISHA. Baki yako ya M-PESA ni KSH263.47.",


"TAD62EDKVQ Imethibitishwa Ksh1.00 imetumwa kwa John  Doe 0729641937 tarehe 13/1/25 saa 5:44 PM. Baki yako ya M-PESA ni Ksh263.47. Gharama ya kutuma ni Ksh0.00.Kiwango cha Pesa unachoweza kutuma kwa siku ni 499,949.00. SAFARICOM HUPIGA NA 0722000000 PEKEE. Kurudisha hizi Pesa,Tuma ujumbe huu kwa 456.",

"TAD72DJ3YB Imethibitishwa. Umepokea Ksh1.00 kutoka John  Doe 0729641937 mnamo 13/1/25 saa 5:39 PM  Baki yako ya M-PESA ni Ksh264.47. SAFARICOM HUPIGA NA 0722000000 PEKEE. Kurudisha hizi pesa, tuma ujumbe huu kwa 456.TAD72CZ6J3 Imethibitishwa.",

"Baki yako ni: Akaunti ya M-PESA : Ksh263.47 Tarehe 13/1/25 saa 5:36 PM. Gharama ya matumizi ni Ksh0.00.",


    ]
    
    for message in test_messages:
        print("\nUjumbe Halisi:", message)
        try:
            result = parser.parse_message(message)
            print("Matokeo:")
            for key, value in result.items():
                print(f"{key}: {value}")
        except Exception as e:
            print(f"Hitilafu wakati wa kuchanganua ujumbe: {str(e)}")

if __name__ == "__main__":
    test_parser()
