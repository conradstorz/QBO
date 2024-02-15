# -*- coding: utf-8 -*-

""" Version 2024.2 qbo_updater / Modify Quickbooks bank downloads to improve importing accuracy
"""


# files to be updated
QBO_FILE_EXT = ".qbo"
DEFAULT_DOWNLOAD_FILENAME = "download.qbo"
BASE_DIRECTORY = "D:/Users/Conrad/Downloads/"
OUTPUT_DIRECTORY = "D:/Users/Conrad/Documents/"

import os
import sys
from loguru import logger
import datetime as dt
from pathlib import Path

from time_strings import LOCAL_NOW_STRING

import re


RUNTIME_NAME = Path(__file__).name
RUNTIME_CWD = Path.cwd()
LN = LOCAL_NOW_STRING()
OS_FILENAME_SAFE_TIMESTR = "".join(i for i in LN if i not in "\/:*?<>|")
QBO_DOWNLOAD_DIRECTORY = Path(BASE_DIRECTORY)
QBO_MODIFIED_DIRECTORY = Path(OUTPUT_DIRECTORY)



BAD_TEXT = [
    r"DEBIT +\d{4}",
    "CKCD ",
    "AC-",
    "POS DB ",
    "POS ",
    "-ONLINE",
    "-ACH",
    "DEBIT",
    "CREDIT",
    "ACH",
    "MISCELLANEOUS",
    "PREAUTHORIZED",
    "PURCHASE TERMINAL",
    "ATM MERCHANT",
    "AUTOMATIC TRANSFER",
]

@logger.catch
def preprocess_memo(memo):
    # Remove specified bad text patterns
    for bad_text in BAD_TEXT:
        if re.match(r".*\d{4}.*", bad_text):  # Check if the bad text is a regex pattern
            memo = re.sub(bad_text, "", memo)
        else:
            memo = memo.replace(bad_text, "")
    
    # Shortening common phrases (if any remain)
    memo = memo.replace("BILL PAYMT", "Bill Pay").strip()

    # Further cleanup to remove extra spaces and standardize spacing
    memo = re.sub(' +', ' ', memo).strip()

    return memo

@logger.catch
def truncate_name(name, max_length=32):
    """Truncate the name value to ensure it does not exceed QuickBooks' limit."""
    return name[:max_length]

@logger.catch
def extract_transaction_details(transaction_lines):
    """Extract details from transaction lines into a dictionary of tag:value."""
    transaction_details = {}
    for line in transaction_lines:
        # Split the line at the first occurrence of ">" to separate the tag from its value
        parts = line.split(">", 1)
        if len(parts) == 2:
            tag, value = parts[0][1:], parts[1]  # Remove the opening "<" from the tag
            transaction_details[tag] = value.strip()
    return transaction_details

@logger.catch
def process_transaction(transaction_lines):
    """Process individual transactions, ensuring memo presence, checking name and memo equality,
    and reformatting back into a list of lines."""
    transaction_details = extract_transaction_details(transaction_lines)
    
    # Ensure there's a memo tag, add a default one if necessary
    if 'MEMO' not in transaction_details:
        transaction_details['MEMO'] = 'No Memo'
    else:
        # memo needs to be stripped of bad text
        transaction_details['MEMO'] = preprocess_memo(transaction_details['MEMO'])
    
    # Check for equality of name and memo
    name = transaction_details.get('NAME', 'No Name')
    memo = transaction_details.get('MEMO')
    if name == memo == 'CHECK PAID':
        # Use checknum for name and refnum for memo if available
        checknum = transaction_details.get('CHECKNUM', 'No CheckNum')
        refnum = transaction_details.get('REFNUM', 'No RefNum')
        transaction_details['NAME'] = checknum
        transaction_details['MEMO'] = refnum
    
    # Convert transaction_details back into a list of lines
    processed_lines = []
    for tag, value in transaction_details.items():
        line = f"<{tag}>{value}\n"
        processed_lines.append(line)
    
    return processed_lines

@logger.catch
def process_qbo_lines2(lines):
    # logger.info(lines)
    modified_lines = []  # Stores the modified lines of the entire file
    transaction_lines = []  # Temporarily stores lines of the current transaction
    processing_transaction = False  # Flag to indicate if we're within a transaction block

    for line in lines:
        # Process header lines to extract date and account number
        if '<DTEND>' in line:
            qbo_file_date = line.replace('<DTEND>', '').replace('</DTEND>', '').strip()
        elif '<ACCTID>' in line:
            account_number = line.replace('<ACCTID>', '').replace('</ACCTID>', '').strip()        

        line_stripped = line.strip()
        if line_stripped.startswith('<STMTTRN>'):
            # Mark the start of a transaction; initialize storage for its lines
            processing_transaction = True
            transaction_lines = [line]  # Start a new transaction block
        elif line_stripped.startswith('</STMTTRN>'):
            # End of transaction found; append the line and process the transaction
            transaction_lines.append(line)
            processing_transaction = False  # Reset the flag as the transaction block ends
            # Process the collected lines of the transaction
            modified_transaction_lines = process_transaction(transaction_lines)
            modified_lines.extend(modified_transaction_lines)  # Add processed lines to the output
        elif processing_transaction:
            # If we are within a transaction, keep collecting its lines
            transaction_lines.append(line)
        else:
            # Lines not part of a transaction are added directly to the output
            modified_lines.append(line)

    # logger.info(modified_lines)
    return modified_lines, qbo_file_date, account_number

@logger.catch
def process_qbo_lines(lines):
    """Takes lines of a Quickbooks QBO file from my bank and repairs shortcomings."""
    modified_lines = []
    qbo_file_date = '19700101'
    account_number = '42'
    in_transaction = False
    # Set default values for all variables to handle missing cases
    name, memo, refnum, checknum = 'No Name', 'No Memo', 'No RefNum', 'No CheckNum'

    for line in lines:

        # watch for date and account number
        if '<DTEND>' in line:
            qbo_file_date = line.strip().replace('<DTEND>', '').replace('</DTEND>', '').strip()
        elif '<ACCTID>' in line:
            account_number = line.strip().replace('<ACCTID>', '').replace('</ACCTID>', '').strip()
            
        if line.strip().startswith('<STMTTRN>'):
            in_transaction = True
            # Reset values with defaults at the start of a new transaction
            name, memo, refnum, checknum = 'No Name', 'No Memo', 'No RefNum', 'No CheckNum'
        elif line.strip().startswith('</STMTTRN>'):
            in_transaction = False
            # Handle the swapping and edge cases for missing fields
            if name == 'CHECK PAID' and memo == 'CHECK PAID':
                modified_lines.append(f'<NAME>{checknum if checknum != "No CheckNum" else "Check"}\n')
                modified_lines.append(f'<MEMO>{refnum if refnum != "No RefNum" else "Ref"}\n')
            else:
                modified_lines.append(f'<NAME>{truncate_name(memo)}\n')
                modified_lines.append(f'<MEMO>{preprocess_memo(name)}\n')
            modified_lines.append('</STMTTRN>\n')
            continue

        if in_transaction:
            if line.strip().startswith('<NAME>'):
                name = line.strip().replace('<NAME>', '').replace('</NAME>', '')
            elif line.strip().startswith('<MEMO>'):
                memo = line.strip().replace('<MEMO>', '').replace('</MEMO>', '')
            elif line.strip().startswith('<REFNUM>'):
                refnum = line.strip().replace('<REFNUM>', '').replace('</REFNUM>', '')
            elif line.strip().startswith('<CHECKNUM>'):
                checknum = line.strip().replace('<CHECKNUM>', '').replace('</CHECKNUM>', '')
            else:
                modified_lines.append(line)
        else:
            modified_lines.append(line)

    return (modified_lines, qbo_file_date, account_number)

@logger.catch
def read_base_file(input_file):
    """read_base_file(Pathlib_Object)
    Return a list of lines contained in base_file.
    """
    try:
        with open(input_file) as IN_FILE:
            file_contents = IN_FILE.readlines()
    except Exception as e:
        logger.error(f"Error in reading {input_file.name}")
        logger.warning(str(e))
        file_contents = []

    if file_contents != []:
        logger.debug(file_contents)
        logger.info("File contents read successfully.")
    return file_contents

@logger.catch
def mylogger(txt):
    """Strip extra newline character from txt to suppress extra blank lines in output

    Args:
        txt (string): text to log

    Returns:
        nothing
    """
    logger.debug(txt.strip())

@logger.catch
def modify_QBO(QBO_records_list, originalfile_pathobj):
    """Take a list of strings from a QBO file format and improve transaction names and memos.
    Wesbanco Bank places all useful info into the memo line. Quickbooks processes transactions based on the names.
    Wesbanco places verbose human readable descriptions in the memo line and a simple transaction number in the name.
    Let's swap those to help quickbooks process the transactions and categorize them.
    Quickbooks limits names of transactions to 32 characters so let's remove the verbose language from the original memos.
    """

    modified_qbo, file_date, acct_number = process_qbo_lines2(QBO_records_list)

    # Attempt to write results to cleanfile
    fname = "".join([file_date, "_", acct_number, QBO_FILE_EXT])
    logger.info(f"Attempting to output to file name: {fname}")
    clean_output_file = Path(QBO_MODIFIED_DIRECTORY, fname)
    try:
        with open(clean_output_file, "w") as f:
            f.writelines(modified_qbo)
    except Exception as e:
        logger.error(f"Error in writing {clean_output_file}")
        logger.warning(str(e))
        sys.exit(1)

    logger.info(f"File {clean_output_file} contents written successfully.")

    logger.info(f"Attempting to remove old {originalfile_pathobj} file...")

    if Path(originalfile_pathobj).exists():
        try:
            os.remove(originalfile_pathobj)
        except OSError as e:
            logger.warning(f"Error: {e.file_path} - {e.strerror}")
            sys.exit(1)
        logger.info(f"Success removing {originalfile_pathobj.name}")

    else:
        logger.warning(f"Sorry, I can not find {originalfile_pathobj.name} file.")

    return

@logger.catch
def process_QBO():
    logger.info("...checking download directory...")
    names = list(QBO_DOWNLOAD_DIRECTORY.glob(f"*{QBO_FILE_EXT}"))
    while names != []:
        # loop while something to process is found

        file_pathobj = names.pop()

        original_records_list = read_base_file(file_pathobj)

        # we have a file, try to process
        logger.info(f"file found to process: {file_pathobj.name}")
        modify_QBO(original_records_list, file_pathobj)
    if names == []:
        logger.info(f"no QBO files found in {QBO_DOWNLOAD_DIRECTORY} directory.")
    return

@logger.catch
def defineLoggers(filename):
    class Rotator:
        # Custom rotation handler that combines filesize limits with time controlled rotation.
        def __init__(self, *, size, at):
            now = dt.datetime.now()
            self._size_limit = size
            self._time_limit = now.replace(
                hour=at.hour, minute=at.minute, second=at.second
            )
            if now >= self._time_limit:
                # The current time is already past the target time so it would rotate already.
                # Add one day to prevent an immediate rotation.
                self._time_limit += dt.timedelta(days=1)

        def should_rotate(self, message, file):
            file.seek(0, 2)
            if file.tell() + len(message) > self._size_limit:
                return True
            if message.record["time"].timestamp() > self._time_limit.timestamp():
                self._time_limit += dt.timedelta(days=1)
                return True
            return False

    # set rotate file if over 500 MB or at midnight every day
    rotator = Rotator(size=5e8, at=dt.time(0, 0, 0))
    # example useage: logger.add("file.log", rotation=rotator.should_rotate)

    # Begin logging definition
    logger.remove()  # removes the default console logger provided by Loguru.
    # I find it to be too noisy with details more appropriate for file logging.

    # INFO and messages of higher priority only shown on the console.
    # it uses the tqdm module .write method to allow tqdm to display correctly.
    # logger.add(lambda msg: tqdm.write(msg, end=""), format="{message}", level="ERROR")

    logger.configure(handlers=[{"sink": os.sys.stderr, "level": "INFO"}])
    # this method automatically suppresses the default handler to modify the message level

    logger.add(
        "".join(["./LOGS/", filename, "_{time}.log"]),
        rotation=rotator.should_rotate,
        level="DEBUG",
        encoding="utf8",
    )
    # create a new log file for each run of the program
    return

@logger.catch
def Main():
    # defineLoggers(f"{RUNTIME_NAME}_{OS_FILENAME_SAFE_TIMESTR}")
    defineLoggers(f"{RUNTIME_NAME}")

    logger.info("Program Start.")  # log the start of the program

    # while True: # loop until user intervention
    process_QBO()
    #    time.sleep(10)

    logger.info("Program End.")

    return

"""Check if this file is being run directly and activate main function if so.
"""
if __name__ == "__main__":
    Main()
