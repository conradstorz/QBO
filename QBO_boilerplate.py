""" this file defines the boilerplate parts of a QBO file.
It should be imported into a program for building QBO files from CSV files.
"""

# qbo file boilerplate
qbo_file_header = """
OFXHEADER:100
DATA:OFXSGML
VERSION:102
SECURITY:NONE
ENCODING:USASCII
CHARSET:1252
COMPRESSION:NONE
OLDFILEUID:NONE
NEWFILEUID:NONE
<OFX>
<SIGNONMSGSRSV1>
<SONRS>
<STATUS>
<CODE>0
<SEVERITY>INFO
</STATUS>
"""
qbo_file_date_header = "<DTSERVER>"
qbo_DTSERVER_date = ""  # to be extracted from csv file
qbo_DTSERVER_time = "120000[-6:CST]"
qbo_file_bank_id_boilerplate = """
<LANGUAGE>ENG
<FI>
<ORG>FundsXpress, Inc
<FID>19953
</FI>
<INTU.BID>19953
</SONRS>
</SIGNONMSGSRSV1>
<BANKMSGSRSV1>
<STMTTRNRS>
<TRNUID>0
<STATUS>
<CODE>0
<SEVERITY>INFO
</STATUS>
<STMTRS>
<CURDEF>USD
<BANKACCTFROM>
<BANKID>121202211
<ACCTID>440024090258
<ACCTTYPE>CHECKING
</BANKACCTFROM>
<BANKTRANLIST>
"""
qbo_DTSTART_date = "<DTSTART>"  # to be appended with actual date
qbo_DTEND_date = "<DTEND>"  # to be appended with actual date
sample_qbo_statement_format = """
<STMTTRN>
<TRNTYPE>DEBIT
<DTPOSTED>20181210120000
<TRNAMT>-490
<FITID>12102018-490AC-BANK OF AMERICA 
<NAME>BANK OF AMERICA -ONLINE PMT
<MEMO>BANK OF AMERICA -ONLINE PMT
</STMTTRN>
"""
qbo_xact_start = "<STMTTRN>"
qbo_xact_end = "</STMTTRN>"
qbo_xact_debit_tag = "<TRNTYPE>DEBIT"
qbo_xact_credit_tag = "<TRNTYPE>CREDIT"
qbo_xact_amount = (
    "<TRNAMT>"
)  # actual amoumt to be appended (negative sign in front of debits)
qbo_xact_unique_id = (
    "<FITID>"
)  # +date+amount+index+memo (maximum 31 characters) (index is a nonce)
nonce_index = 4095  # 3 digit hex counter counting down from 4095(fff)
qbo_xact_memo = "<MEMO>"  # +up to 64 characters
qbo_xact_name = "<NAME>"  # + nomore than 31 characters
qbo_file_final_boilerplate = """
</BANKTRANLIST>
<LEDGERBAL>
<BALAMT>0
<DTASOF>20181231000000.000[-6:CST]
</LEDGERBAL>
<AVAILBAL>
<BALAMT>0
<DTASOF>20181231000000.000[-6:CST]
</AVAILBAL>
</STMTRS>
</STMTTRNRS>
</BANKMSGSRSV1>
</OFX>
"""

# text to remove from transaction descriptions
bad_text = [r"DEBIT +\d{4}", "CKCD ", "AC-", "POS ", "POS DB "]

qbo_file_date_tag = "<DTEND>"
file_date = "notFound"
acct_number_tag = "<ACCTID>"
acct_number = "notFound"
