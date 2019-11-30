""" file csv2qbo.py
initial version compatible with schwab.com checking csv downloads
"""
# csv2qbo / Modify csv bank downloads into qbo file format

from pathlib import Path
home = str(Path.home()) # gather the home directory

import os
runtime_name = os.path.basename(__file__)

import re
import csv
import sys
import time
from loguru import logger
from dateutil.parser import parse
from hashids import Hashids
from QBO_boilerplate import *


# files to be updated
base_file_extension = ".csv"
filename = "download.csv"
basedirectory = home + "/Downloads/"
outputdirectory = home + "/Documents/"
output_file_extension = ".qbo"

# header line for schwab.com downloads
schwabHeader = "Transactions  for Checking account XXXXXX-090258"


@logger.catch
def Fix_date(string):
    """Fix_date(time in any format)
    return date in quickbooks qbo format
    """
    dt = parse(string)
    return dt.strftime("%Y%m%d")

@logger.catch
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


# establish logger state
#FORMAT = "%(asctime)-15s %(clientip)s %(user)-8s %(message)s"
#logger.basicConfig(format=FORMAT, level=logger.INFO)
#d = {"clientip": "xxx.xxx.xxx.xxx", "user": "qbo_loggs"}
# logger.warning('Protocol problem: %s', 'connection reset')


@logger.catch
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
        logger.error("Error in reading " + base_file)
        logger.warning(str(e))

    if csv_lines != []:
        logger.debug(csv_lines)
        logger.info("File csv lines read successfully.")

    return csv_output

@logger.catch
def Clean_Line(text_list, line):
    """Clean_Line(text list to be removed, text to have modified)
    Return line with redundant spaces removed and text deleted if exists.
    """
    new_line = re.sub(r" +", " ", line)  # remove duplicate spaces from within line
    for t in text_list:
        # remove each occurance from new_line
        new_line = re.sub(t, "", new_line)
        logger.debug(new_line)
    return (
        new_line.strip()
    )  # returns line without leading or trailing whitespace or newline

@logger.catch
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

@logger.catch
def strip_nonPosted(lines):
    not_posted = True
    posted_xacts = []
    for line in lines:  # first strip unwanted headers and pending xacts
        if not_posted:
            logger.debug(f'not_posted: {", ".join(line)}')
            if line[0] == "Posted Transactions":
                not_posted = False
        else:
            logger.debug(f'posted: {", ".join(line)}')
            posted_xacts.append(line)
    return posted_xacts

@logger.catch
def convert_schwab_csv_file(lines, text):
    """convert_schwab_csv_file(list of lines, list of text strings to remove)
    Remove unwanted text from transaction data from bank download in quickbooks format.
    This routine takes csv transactions from Schwab bank and outputs a QBO compatible file.
    csv file posted transaction lines have the following header:
    Date,Type,Check #,Description,Withdrawal (-),Deposit (+),RunningBalance
    also:
        dollar amounts include a leading dollar sign and are always stated as a positive number.
        values are sometimes enclosed in quotes
    """
    global file_date, acct_number
    qbo_file_lines = [] # start to build QBO output format
    qbo_file_lines.append(qbo_file_header)
    posted_xacts = strip_nonPosted(lines)
    if posted_xacts == []:
        logger.info("No POSTED transactions found.")
        return qbo_file_lines.append(qbo_file_final_boilerplate)
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


@logger.catch
def defineLoggers():
    logger.configure(
        handlers=[{"sink": os.sys.stderr, "level": "DEBUG"}]
    )  # this method automatically suppresses the default handler to modify the message level
 
    logger.add(
        runtime_name + "_{time}.log", level="DEBUG"
    )  # create a new log file for each run of the program
    return


@logger.catch
def getFileList(target_directory, base_Extension):
    names = os.listdir(target_directory)  
    for name in names:
        if name.endswith(base_Extension):
            logger.debug(name)
    return names


@logger.catch
def process_file(originalfile, bad_text):
    # we have a file, try to process
    result = convert_schwab_csv_file(originalfile, bad_text)
    if result == []:
        logger.error("Failed to convert:  %s" % originalfile)
        sys.exit(1)

    # Attempt to write results to cleanfile
    cf = outputdirectory + file_date + "_" + acct_number + output_file_extension
    try:
        with open(cf, "w") as f:
            f.writelines(result)
    except Exception as e:
        logger.error("Error in writing %s" % cf)
        logger.warning(str(e))
        sys.exit(1)

    logger.info("File %s contents written successfully." % cf)
    return cf


@logger.catch
def remove_file(FQ_file_path):
    logger.info("Attempting to remove old %s file..." % FQ_file_path)

    if os.path.exists(FQ_file_path):
        try:
            os.remove(FQ_file_path)
        except OSError as e:
            logger.warning("Error: %s." % e)
            return 2
        logger.info("Success removing %s" % FQ_file_path)
        return 0

    else:
        logger.info("Sorry, I can not find %s file." % FQ_file_path)
        return 1
    return None


@logger.catch
def Main():
    defineLoggers()
    logger.info("Program Start.")  # log the start of the program
    logger.info(runtime_name)
    # declare program start
    logger.info("Program Start: %s" % "nominal")

    while True:
        # loop until something to process is found
        logger.info("...checking download directory...")
        files = getFileList(basedirectory, base_file_extension)
        FQ_file_path = os.path.join(basedirectory, filename)
        originalfile = read_csv_file(FQ_file_path)

        if originalfile == []:
            logger.info("File not yet found %s. sleeping 10 seconds..." % FQ_file_path)
            time.sleep(10)
        else:
            clean_f = process_file(originalfile, bad_text)
            remove_file(FQ_file_path)
            # declare program end
            logger.info("Program End: %s" % "nominal")
            sys.exit(0)
    return None

# TDD test code sample
def HelloWorld():
    pass

"""Check if this file is being run directly
"""
if __name__ == "__main__":
    # Run the processes as that seems to be the purpose
    Main()
    