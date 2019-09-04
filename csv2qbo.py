""" file csv2qbo.py
initial version compatible with schwab.com checking csv downloads
"""
# csv2qbo / Modify csv bank downloads into qbo file format

from pathlib import Path
home = str(Path.home()) # gather the home directory


# files to be updated
base_file_extension = ".csv"
filename = "download.csv"
basedirectory = home + "/Downloads/"
outputdirectory = home + "/Documents/"
output_file_extension = ".qbo"

# header line for schwab.com downloads
schwabHeader = "Transactions  for Checking account XXXXXX-090258"

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
file_date = ""
acct_number_tag = "<ACCTID>"
acct_number = ""

import os
import re
import csv
import sys
import time
import logging
from dateutil.parser import parse
from hashids import Hashids


def Fix_date(string):
    """Fix_date(time in any format)
    return date in quickbooks qbo format
    """
    dt = parse(string)
    return dt.strftime("%Y%m%d")


def hashID(string):
    """hashID(string representation of a number)
    return a hash of the value represented by string
    Method being used works with integers and this implementation
    passes strings representing dollar values so amounts are multiplied by 100
    to achieve an integer value in pennies.
    """

    #   Here in csv2qbo.py I need to create an ID for quickbooks to identify
    #   each transaction and if these IDs are not unique they are considered duplicates.
    #   An early iteration of csv2qbo.py used date and time plus memo as the ID. This would
    #   normally have worked but for a time when multiple otherwise identical transactions
    #   appeared on the same buisness day. I realized the only unique information i had
    #   available was the banks own running balance that they report along with each transaction.
    #   I had been discarding that value since it served me no purpose. I decided to hash it to
    #   obfuscate the meaning while creating an ID that was repeateable on seperate runs of the
    #   utility against CSV files from the bank. This helps eliminate TRUE duplicates from quickbooks
    #   when I might happen to download CSV files that overlap previous CSV file downloads already
    #   imported into quickbooks. An earlier implemntation used a random NONCE inserted into the
    #   ID string but this was not repeatable over different CSV downloads.

    hashids = Hashids()  # create an instance of the module object
    cleaned = string.replace(",", "")  # remove any commas
    return hashids.encode(int(float(cleaned.strip("$")) * 100))


# establish logging state
FORMAT = "%(asctime)-15s %(clientip)s %(user)-8s %(message)s"
logging.basicConfig(format=FORMAT, level=logging.INFO)
d = {"clientip": "xxx.xxx.xxx.xxx", "user": "qbo_loggs"}
# logging.warning('Protocol problem: %s', 'connection reset', extra=d)

# declare program start
logging.info("Program Start: %s", "nominal", extra=d)


def read_csv_file(base_file):
    """read_base_file(fully qualified filename)
    Return a list of lines contained in base_file.
    """
    csv_lines = []
    csv_output = []
    try:
        with open(base_file) as csv_file:
            csv_lines = csv.reader(csv_file, delimiter=",")
            for row in csv_lines:  # convert from csv object to list
                csv_output.append(row)

    except Exception as e:
        logging.error("Error in reading %s", base_file, extra=d)
        logging.warning(str(e), extra=d)

    if csv_lines != []:
        logging.debug(csv_lines, extra=d)
        logging.info("File csv lines read successfully.", extra=d)

    return csv_output


def Clean_Line(text_list, line):
    """Clean_Line(text list to be removed, text to have modified)
    Return line with redundant spaces removed and text deleted if exists.
    """
    new_line = re.sub(r" +", " ", line)  # remove duplicate spaces from within line
    for t in text_list:
        # remove each occurance from new_line
        new_line = re.sub(t, "", new_line)
        logging.debug(new_line, extra=d)
    return (
        new_line.strip()
    )  # returns line without leading or trailing whitespace or newline


def create_qbo_statement_block(xact):
    """create_qbo_statement_block(xact in form of a list)
        convert csv row in the form of:
            Date,Type,Check #,Description,Withdrawal (-),Deposit (+),RunningBalance
        into a qbo statement in the form of:
            sample_qbo_statement_format
            converting debits and credits into the correct form
            and adding a nonce to the FITID to make each one unique to quickbooks
    """
    global nonce_index
    maximum_nametag_line_length = 31

    if xact[1] == "CHECK":
        debit_credit = "CHECK"
        amount = "-" + xact[4][1:]
    else:
        debit_credit = "DEBIT"
        amount = "0"
        if xact[5] != "":  # csv position 5 is blank for debits
            debit_credit = "CREDIT"
            amount = xact[5][1:]
        else:
            amount = "-" + xact[4][1:]
    amount = amount.strip()

    description = Clean_Line(bad_text, xact[3])
    xact_date = Fix_date(xact[0])
    # fit_id = xact_date + amount + hex(nonce_index)[2:] + description
    # nonce_index -= 1 # update nonce after use
    fit_id = (
        xact_date + amount + hashID(xact[6]) + description
    )  # xact[6] is the banks own running balance
    fit_id = fit_id[:maximum_nametag_line_length]
    xact_name = description[:maximum_nametag_line_length]
    xact_memo = description
    formatted_transaction = []
    formatted_transaction.append("<STMTTRN>" + "\n")
    formatted_transaction.append("<TRNTYPE>" + debit_credit + "\n")
    formatted_transaction.append("<DTPOSTED>" + xact_date + "\n")
    formatted_transaction.append("<TRNAMT>" + amount + "\n")
    formatted_transaction.append("<FITID>" + fit_id + "\n")
    if xact[1] == "CHECK":
        formatted_transaction.append("<CHECKNUM>" + xact[2] + "\n")
    formatted_transaction.append("<NAME>" + xact_name + "\n")
    formatted_transaction.append("<MEMO>" + xact_memo + "\n")
    formatted_transaction.append("</STMTTRN>" + "\n")
    return formatted_transaction


def convert_csv_file(lines, text):
    """convert_csv_file(list of lines, list of text strings to remove)
    Remove unwanted text from transaction data from bank download in quickbooks format.
    This routine takes csv transactions from Schwab bank and outputs a QBO compatible file.
    csv file posted transaction lines have the following header:
    Date,Type,Check #,Description,Withdrawal (-),Deposit (+),RunningBalance
    also:
        dollar amounts include a leading dollar sign and are always stated as a positive number.
        values are sometimes enclosed in quotes
    """
    global file_date, acct_number

    qbo_file_lines = []
    qbo_file_lines.append(qbo_file_header)

    # qbo_file_lines.append()
    # print(lines)
    not_posted = True
    posted_xacts = []
    for line in lines:  # first strip unwanted headers and pending xacts
        # print(line)
        if not_posted:
            logging.debug(f'not_posted: {", ".join(line)}', extra=d)
            if line[0] == "Posted Transactions":
                not_posted = False
        else:
            logging.debug(f'posted: {", ".join(line)}', extra=d)
            posted_xacts.append(line)
    if posted_xacts == []:
        logging.info("No POSTED transactions found.", extra=d)
        return qbo_file_lines

    # print(posted_xacts)
    file_date = Fix_date(
        posted_xacts[0][0]
    )  # most recent date is same as first xact date
    qbo_DTSERVER_date = (
        qbo_file_date_header + file_date + qbo_DTSERVER_time
    )  # full datetimestamp format

    qbo_file_lines.append(qbo_DTSERVER_date)

    qbo_file_lines.append(qbo_file_bank_id_boilerplate)

    least_recent = Fix_date(
        posted_xacts[-1][0]
    )  # last xact contains the most remote date
    qbo_file_lines.append(qbo_DTSTART_date + least_recent + "\n")

    qbo_file_lines.append(qbo_DTEND_date + file_date + "\n")

    for line in posted_xacts:
        for item in create_qbo_statement_block(line):
            qbo_file_lines.append(item)

    qbo_file_lines.append(qbo_file_final_boilerplate)

    return qbo_file_lines


def Main():
    while True:
        # loop until something to process is found
        logging.info("...checking download directory...", extra=d)
        for name in os.listdir(basedirectory):
            if name.endswith(base_file_extension):
                print(name)
        file_path = os.path.join(basedirectory, filename)

        originalfile = read_csv_file(file_path)

        if originalfile == []:
            logging.info("File not yet found %s. sleeping 10 seconds..." % file_path, extra=d)
            time.sleep(10)
        else:
            # we have a file, try to process
            result = convert_csv_file(originalfile, bad_text)
            if result == []:
                sys.exit(1)

            # Attempt to write results to cleanfile
            cf = outputdirectory + file_date + "_" + acct_number + output_file_extension
            try:
                with open(cf, "w") as f:
                    f.writelines(result)
            except Exception as e:
                logging.error("Error in writing %s", cf, extra=d)
                logging.warning(str(e), extra=d)
                sys.exit(1)

            logging.info("File %s contents written successfully." % cf, extra=d)

            logging.info("Attempting to remove old %s file..." % file_path, extra=d)

            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except OSError as e:
                    logging.warning(
                        "Error: %s - %s." % (e.file_path, e.strerror), extra=d
                    )
                    sys.exit(1)
                logging.info("Success removing %s" % file_path, extra=d)

            else:
                logging.info("Sorry, I can not find %s file." % file_path, extra=d)

            # declare program end
            logging.info("Program End: %s", "nominal", extra=d)
            sys.exit(0)
    return


"""Check if this file is being run directly
"""
if __name__ == "__main__":
    # Run the processes as that seems to be the purpose
    Main()
    