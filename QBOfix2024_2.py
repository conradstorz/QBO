# -*- coding: utf-8 -*-

""" Version 2024.2 qbo_updater / Modify Quickbooks bank downloads to improve importing accuracy
"""

import os
import sys
from loguru import logger
import datetime as dt
from pathlib import Path
from time_strings import LOCAL_NOW_STRING
import re

# files to be updated
QBO_FILE_EXT = ".qbo"
DEFAULT_DOWNLOAD_FILENAME = "download.qbo"
BASE_DIRECTORY = "D:/Users/Conrad/Downloads/"
OUTPUT_DIRECTORY = "D:/Users/Conrad/Documents/"
RUNTIME_NAME = Path(__file__).name
RUNTIME_CWD = Path.cwd()
LN = LOCAL_NOW_STRING()
OS_FILENAME_SAFE_TIMESTR = "".join(i for i in LN if i not in r"\:/*?<>|")
QBO_DOWNLOAD_DIRECTORY = Path(BASE_DIRECTORY)
QBO_MODIFIED_DIRECTORY = Path(OUTPUT_DIRECTORY)
BAD_TEXT = [
    r"DEBIT +\d{4}",
    "CKCD ",  # the space included here ensures that this string is not part of a bigger word
    "AC-",  # no space here allows this substring to be removed from a string
    "POS DB ",
    "POS ",  # 'pos' won't be removed from words like 'position'
    "-ONLINE ",
    "-ACH ",
    "DEBIT ",
    "CREDIT ",
    "ACH ",  # possibly i need to consider how these strings are handled by the cleaning routine.
    "MISCELLANEOUS ",  # 'ach ' would probably match 'reach ' and result in 're'
    "PREAUTHORIZED ",
    "PURCHASE ",
    "TERMINAL ",
    "ATM ",
    "MERCHANT ",
    "AUTOMATIC ",
    "TRANSFER ",
]


@logger.catch
def preprocess_memo(memo):
    # Remove specified bad text patterns
    logger.debug(f"Original memo line:{memo}")
    for bad_text in BAD_TEXT:
        if re.match(r".*\d{4}.*", bad_text):  # Check if the bad text is a regex pattern
            memo = re.sub(bad_text, "", memo)
        else:
            memo = memo.replace(bad_text, "")
    # Shortening common phrases (if any remain)
    memo = memo.replace("BILL PAYMT", "BillPay").strip()
    # Further cleanup to remove extra spaces and standardize spacing
    memo = re.sub(' +', ' ', memo).strip()
    logger.debug(f"Cleaned memo:{memo}")
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
            if parts[0].startswith('<'):  # is this a valid tag?
                tag, value = parts[0][1:], parts[1]  # Remove the opening "<" from the tag
                transaction_details[tag] = value.strip()
    logger.debug(transaction_details)
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
        # memo needs to be stripped of bad text and truncated
        transaction_details['MEMO'] = truncate_name(preprocess_memo(transaction_details['MEMO']))
    logger.debug(transaction_details)
    # Check for equality of name and memo
    if 'NAME' not in transaction_details:
        transaction_details['NAME'] = 'No Name'
    name = transaction_details['NAME']
    memo = transaction_details['MEMO']
    if name == memo == 'CHECK PAID':
        # Use checknum for name and refnum for memo if available
        checknum = transaction_details.get('CHECKNUM', 'No CheckNum')
        refnum = transaction_details.get('REFNUM', 'No RefNum')
        transaction_details['NAME'] = checknum
        transaction_details['MEMO'] = refnum
    else:
        # name and memo are different so we need to swap their values using the power of tuple unpacking
        transaction_details['NAME'], transaction_details['MEMO'] = transaction_details['MEMO'], transaction_details.get('NAME', 'No Name')
    logger.debug(transaction_details)
    # Convert transaction_details back into a list of lines
    processed_lines = []
    for tag, value in transaction_details.items():
        line = f"<{tag}>{value}\n"
        processed_lines.append(line)
    return processed_lines


@logger.catch
def process_qbo_lines(lines):
    qbo_file_date = '19700101'  # default value incase no date found
    account_number = '42'  # default  
    modified_lines = []  # Stores the modified lines of the entire file
    transaction_lines = []  # Temporarily stores lines of the current transaction
    processing_transaction = False  # Flag to indicate if we're within a transaction block
    xacts_found = 0  # initialize counter of transactions found
    for line in lines:
        line_stripped = line.strip()        
        # Process header lines to extract date and account number
        if line_stripped.startswith('<DTEND>'):
            qbo_file_date = line_stripped.replace('<DTEND>', '')
        elif line_stripped.startswith('<ACCTID>'):
            account_number = line_stripped.replace('<ACCTID>', '')        
        if line_stripped.startswith('<STMTTRN>'):
            processing_transaction = True  # Mark the start of a transaction
            xacts_found += 1  # increment counter
            transaction_lines = [line]  # Start a new transaction block
        elif line_stripped.startswith('</STMTTRN>'):
            # End of transaction found
            transaction_lines.append(line)  # append the line
            processing_transaction = False  # Reset the flag as the transaction block ends
            modified_transaction_lines = process_transaction(transaction_lines)  # Process the collected lines of the transaction
            modified_lines.extend(modified_transaction_lines)  # Add processed lines to the output
        elif processing_transaction:
            # If we are within a transaction, keep collecting its lines
            transaction_lines.append(line)
        else:
            # Lines not part of a transaction are added directly to the output
            modified_lines.append(line)
    logger.info(f"{xacts_found} transactions found.")
    logger.debug(modified_lines)  # TODO make this output more log friendly
    return modified_lines, qbo_file_date, account_number



@logger.catch
def read_base_file(input_file):
    """read_base_file(Pathlib_Object)
    Return a list of lines contained in base_file.
    """
    logger.info(f"Attempting to open input file {input_file.name}")
    try:
        with open(input_file) as IN_FILE:
            file_contents = IN_FILE.readlines()
    except Exception as e:
        logger.error(f"Error in reading {input_file.name}")
        logger.warning(str(e))
        file_contents = []
    if file_contents != []:
        logger.info("File contents read successfully.")
    return file_contents


@logger.catch
def modify_QBO(QBO_records_list, originalfile_pathobj):
    """Take a list of strings from a QBO file format and improve transaction names and memos.
    Wesbanco Bank places all useful info into the memo line. Quickbooks processes transactions based on the names.
    Wesbanco places verbose human readable descriptions in the memo line and a simple transaction number in the name.
    Let's swap those to help quickbooks process the transactions and categorize them.
    Quickbooks limits names of transactions to 32 characters so let's remove the verbose language from the original memos.
    """
    modified_qbo, file_date, acct_number = process_qbo_lines(QBO_records_list)
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
        logger.info(f"no QBO files remain in {QBO_DOWNLOAD_DIRECTORY} directory.")
    return


def defineLoggers(filename):
    def should_rotate(message, file):
        # Determine if log file should rotate based on size
        filesize_limit = 5e8  # 500 MB
        # Rotate file if over size limit
        file.seek(0, 2)  # Move to the end of the file to get its size
        if file.tell() > filesize_limit:
            return True
        return False

    # Configure loguru logger
    logger.remove()  # Remove default handler to avoid duplicate logging
    # Define log path with a date, ensuring all entries for a day go to the same file
    log_directory = "./LOGS/"
    os.makedirs(log_directory, exist_ok=True)  # Ensure log directory exists
    daily_log_filename = f"{filename}_{dt.datetime.now():%Y%m%d}.log"
    log_path = os.path.join(log_directory, daily_log_filename)
    logger.add(log_path, rotation=should_rotate, level="DEBUG", encoding="utf8", retention="10 days")
    logger.add(sys.stderr, level="INFO")  # Optional: Add a console handler if needed
    print(f"Logging to {log_path}")


@logger.catch
def Main():
    defineLoggers(f"{RUNTIME_NAME}")
    logger.info("Program Start.")  # log the start of the program
    process_QBO()
    logger.info("Program End.")
    return


"""Check if this file is being run directly and activate main function if so.
"""
if __name__ == "__main__":
    Main()
