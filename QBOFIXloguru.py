# -*- coding: utf-8 -*-

""" qbo_updater / Modify Quickbooks bank downloads to improve importing accuracy
"""


# files to be updated
QBO_FILE_EXT = ".qbo"
DEFAULT_DOWNLOAD_FILENAME = "download.qbo"
BASE_DIRECTORY = "D:/Users/Conrad/Downloads/"
OUTPUT_DIRECTORY = "D:/Users/Conrad/Documents/"

# text to remove from transaction descriptions
# TODO: make this a dict with contractions as available replacement strings not just ""
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


import os
import re
import sys
from loguru import logger
import datetime as dt
from pathlib import Path

from time_strings import LOCAL_NOW_STRING

RUNTIME_NAME = Path(__file__).name
RUNTIME_CWD = Path.cwd()
LN = LOCAL_NOW_STRING()
OS_FILENAME_SAFE_TIMESTR = "".join(i for i in LN if i not in "\/:*?<>|")
QBO_DOWNLOAD_DIRECTORY = Path(BASE_DIRECTORY)
QBO_MODIFIED_DIRECTORY = Path(OUTPUT_DIRECTORY)


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
def Clean_Line(bad_word, original_text):
    """Clean_Line(text to be removed, text to have modified)
    Return line with redundant spaces removed and text deleted if exists.
    """
    stripped_text = re.sub(
        r" +", " ", original_text
    )  # remove duplicate spaces from within line
    cleaned_text = re.sub(bad_word, "", stripped_text)
    return cleaned_text.strip()


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
def clean_qbo_file(lines, bad_text):
    """clean_qbo_file(list of lines, list of text strings to remove)
    Remove unwanted text from transaction data from bank download in quickbooks format.
    My bank provides poorly formatted data. Quickbooks loses access to data due to
    the fact that the memo line has a longer line length than allowed by quickbooks.
    This function replaces the nametag with the cleaned memotag data and the memotag becomes the value of the original nametag.

    Steps:
        import the strings to identify the transactions.
        copy the memo and clean out all the verbose stings (BAD_TEXT) and truncate to the quickbooks limit.
        NOTE: TODO: BAD_TEXT should be formatted as {'match_string': 'replacement_string'}
        set the memo equal to the value of original transaction name.
        set the name equal to the value of the cleaned memo line.
        TODO: Implement a list of rules for identifing transactions and improving the data.
            e.g. An amount match for transactions to give them a unique name (quickbooks only matches on names)

    """
    TRANS_START_TAG = "<STMTTRN>"
    TRANS_END_TAG = "</STMTTRN>"
    QBO_FILE_DATE_TAG = "<DTEND>"
    ACCOUNT_NUMBER_TAG = "<ACCTID>"
    file_date, acct_number = "nodate", "nonumber"
    maximum_nametag_line_length = 32
    MEMO_TAG = "<MEMO>"
    NAME_TAG = "<NAME>"
    REFNUM_TAG = "<REFNUM>"
    clean_file_lines = []

    while lines != []:
        # pop first line
        line = lines.pop(0)
        logger.debug(f"INPUT:{line.strip()}")

        # monitor data stream for date and acct number
        if line.startswith(QBO_FILE_DATE_TAG):
            # extract file date for use with naming output file
            file_date = line.replace(QBO_FILE_DATE_TAG, "").lstrip().rstrip()
            logger.info(f"Date Found:{file_date.strip()}")

        if line.startswith(ACCOUNT_NUMBER_TAG):
            # extract bank account number for use in naming output file
            acct_number = line.replace(ACCOUNT_NUMBER_TAG, "").lstrip().rstrip()
            logger.info(f"Account Number found:{acct_number.strip()}")

        # monitor for transaction start
        if line.startswith(TRANS_START_TAG) == True:
            logger.debug(f"Transaction found...")
            # load transaction into temp storage
            transaction_lines = []
            while line.startswith(TRANS_END_TAG) == False:
                transaction_lines.append(line)
                line = lines.pop(0)
                logger.debug(f"INPUT:{line.strip()}")

            # find memo and name items in transaction
            memo_data_index = -1
            name_data_index = -1
            refnum_data_index = -1
            for indx, item in enumerate(transaction_lines):
                if item.startswith(MEMO_TAG):
                    logger.debug(f"MEMO line is index::{indx}")
                    memo_data_index = indx
                if item.startswith(NAME_TAG):
                    logger.debug(f"NAME line is index::{indx}")
                    name_data_index = indx
                if item.startswith(REFNUM_TAG):
                    logger.debug(f"REFNUM line is index::{indx}")
                    refnum_data_index = indx

            # EDGE CASES
            if memo_data_index == -1:  # there is no memo line in the bank download
                logger.warning("MEMO is missing from the current transaction.")
                memo_data_index = refnum_data_index + 2
                transaction_lines.insert(
                    refnum_data_index + 2,
                    f"{transaction_lines[refnum_data_index].replace(REFNUM_TAG, '').lstrip()}",
                )
                
            if name_data_index == -1:  # This has never happened in my experience
                logger.warning("NAME is missing from the current transaction.")
                name_data_index = refnum_data_index + 1
                transaction_lines.insert(refnum_data_index + 1, f"BLANK\n")

            # process memo data
            memo_data = (
                transaction_lines[memo_data_index].replace(MEMO_TAG, "").lstrip()
            )  # remove memotag
            logger.info(f"Removing bad text from memo line...")
            for item in bad_text:
                # remove each occurance from the memo data
                memo_data = Clean_Line(item, memo_data)
                # EDGE CASE: do not allow memo to be empty
            logger.debug(f'ORIGINAL: {transaction_lines[memo_data_index].replace(MEMO_TAG, "").lstrip()}')
            logger.debug(f' CLEANED: {memo_data}')
            if len(memo_data) < 1:
                logger.warning('NOTE: memo line contained no text after cleaning.')
                memo_data = 'NOTHING USEFUL'

            # place name value into memo line because my bank puts them in the wrong places
            name_data = (
                transaction_lines[name_data_index].replace(NAME_TAG, "").lstrip()
            )  # remove nametag
            logger.debug(f"Saving new memo:{name_data.strip()}")
            transaction_lines[memo_data_index] = (
                MEMO_TAG + name_data
            )  # name data still has carriage return and does not need it added like the memo_data variable does.

            # place cleaned memo data into name line and truncate length to quickbooks limit
            logger.debug(f"Saving new name:{memo_data.strip()}")
            transaction_lines[name_data_index] = (
                NAME_TAG + memo_data[:maximum_nametag_line_length] + "\n"
            )

            # EDGE CASE: If name and memo are equal set memo to refnum and name to "COLLISION".
            if transaction_lines[name_data_index].replace(NAME_TAG, "").lstrip() == transaction_lines[memo_data_index].replace(MEMO_TAG, ""):
                logger.debug(f'EDGE CASE found: name and memo are identical. {transaction_lines[name_data_index].replace(NAME_TAG, "").lstrip()}')
                transaction_lines[memo_data_index] = (MEMO_TAG + transaction_lines[refnum_data_index].replace(REFNUM_TAG, '').lstrip())
                transaction_lines[name_data_index] = (NAME_TAG + "COLLISION")

            # place transaction data into output list now
            for item in transaction_lines:
                clean_file_lines.append(item)
                logger.debug(f"OUTPUT:{item.strip()}")

        # place data into output list
        logger.debug(f"OUTPUT:{line.strip()}")
        clean_file_lines.append(line)

    return (
        clean_file_lines,  # return lines in same order as submitted
        file_date,
        acct_number,
    )


@logger.catch
def modify_QBO(QBO_records_list, originalfile_pathobj):
    """Take a list of strings from a QBO file format and improve transaction names and memos.
    Wesbanco Bank places all useful info into the memo line. Quickbooks processes transactions based on the names.
    Wesbanco places verbose human readable descriptions in the memo line and a simple transaction number in the name.
    Let's swap those to help quickbooks process the transactions and categorize them.
    Quickbooks limits names of transactions to 32 characters so let's remove the verbose language from the original memos.
    """

    modified_qbo, file_date, acct_number = clean_qbo_file(QBO_records_list, BAD_TEXT)

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
        modify_QBO(original_records_list, file_pathobj)

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


"""12/8/2023 asked chatgpt to refactor the clean_qbo_file function. The result is below.

import re

def parse_qbo_data(lines):
    file_date, acct_number = "nodate", "nonumber"
    clean_file_lines = []

    for line in lines:
        if line.startswith("<DTEND>"):
            file_date = line.replace("<DTEND>", "").strip()
        elif line.startswith("<ACCTID>"):
            acct_number = line.replace("<ACCTID>", "").strip()
        clean_file_lines.append(line)

    return file_date, acct_number, clean_file_lines

def clean_memo_and_name(transaction_lines, bad_text, maximum_nametag_line_length):
    MEMO_TAG = "<MEMO>"
    NAME_TAG = "<NAME>"
    REFNUM_TAG = "<REFNUM>"

    memo_data_index = -1
    name_data_index = -1
    refnum_data_index = -1

    for indx, item in enumerate(transaction_lines):
        if item.startswith(MEMO_TAG):
            memo_data_index = indx
        if item.startswith(NAME_TAG):
            name_data_index = indx
        if item.startswith(REFNUM_TAG):
            refnum_data_index = indx

    if memo_data_index == -1:
        memo_data_index = refnum_data_index + 2
        transaction_lines.insert(
            refnum_data_index + 2,
            f"{transaction_lines[refnum_data_index].replace(REFNUM_TAG, '').strip()}",
        )

    if name_data_index == -1:
        name_data_index = refnum_data_index + 1
        transaction_lines.insert(refnum_data_index + 1, "BLANK\n")

    memo_data = transaction_lines[memo_data_index].replace(MEMO_TAG, "").strip()
    for item in bad_text:
        memo_data = re.sub(re.escape(item), "", memo_data)

    if len(memo_data) < 1:
        memo_data = "NOTHING USEFUL"

    name_data = transaction_lines[name_data_index].replace(NAME_TAG, "").strip()
    transaction_lines[memo_data_index] = MEMO_TAG + name_data
    transaction_lines[name_data_index] = (
        NAME_TAG + memo_data[:maximum_nametag_line_length] + "\n"
    )

    if (
        transaction_lines[name_data_index]
        .replace(NAME_TAG, "")
        .strip() == transaction_lines[memo_data_index].replace(MEMO_TAG, "").strip()
    ):
        transaction_lines[memo_data_index] = (
            MEMO_TAG
            + transaction_lines[refnum_data_index]
            .replace(REFNUM_TAG, "")
            .strip()
        )
        transaction_lines[name_data_index] = NAME_TAG + "COLLISION"

    return transaction_lines

def refactoring_clean_qbo_file(lines, bad_text):
    maximum_nametag_line_length = 32
    clean_file_lines = []

    file_date, acct_number, clean_file_lines = parse_qbo_data(lines)

    i = 0
    while i < len(clean_file_lines):
        if clean_file_lines[i].startswith("<STMTTRN>"):
            transaction_lines = clean_file_lines[i:]
            transaction_lines = clean_memo_and_name(
                transaction_lines, bad_text, maximum_nametag_line_length
            )
            clean_file_lines[i:] = transaction_lines
        i += 1

    return clean_file_lines, file_date, acct_number



"""

"""Here are some suggested tests.

import pytest
from hypothesis import given, settings, strategies as st

# Import your individual functions here

# Define a strategy for generating QBO data lines
qbo_data_strategy = st.lists(
    st.text(
        alphabet=st.characters(
            whitelist_categories=("Lu", "Ll", "Nd", "Zs"),  # Letters, Numbers, Spaces
            blacklist_characters=("<", ">", "\n"),
        ),
        min_size=1,
        max_size=50,  # Adjust the maximum line length as needed
    ),
    min_size=1,
    max_size=50,  # Adjust the number of lines generated as needed
)

# Define a strategy for generating bad_text
bad_text_strategy = st.lists(st.text(min_size=1, max_size=10), min_size=0, max_size=5)

@given(qbo_data=qbo_data_strategy, bad_text=bad_text_strategy)
@settings(deadline=None)  # Disable deadline to allow longer test runs
def test_parse_qbo_data_with_hypothesis(qbo_data, bad_text):
    # Test the parse_qbo_data function with generated data
    file_date, acct_number, clean_file_lines = parse_qbo_data(qbo_data)

    # Perform assertions based on your requirements
    # ...

@given(qbo_data=qbo_data_strategy, bad_text=bad_text_strategy)
@settings(deadline=None)  # Disable deadline to allow longer test runs
def test_clean_memo_and_name_with_hypothesis(qbo_data, bad_text):
    # Test the clean_memo_and_name function with generated data
    transaction_lines = qbo_data  # Replace with appropriate data
    maximum_nametag_line_length = 32  # Replace with the desired length

    cleaned_memo, cleaned_name = clean_memo_and_name(
        transaction_lines, bad_text, maximum_nametag_line_length
    )

    # Perform assertions based on your requirements
    # ...

@given(qbo_data=qbo_data_strategy, bad_text=bad_text_strategy)
@settings(deadline=None)  # Disable deadline to allow longer test runs
def test_swap_and_adjust_with_hypothesis(qbo_data, bad_text):
    # Test the swap_and_adjust function with generated data
    transaction_lines = qbo_data  # Replace with appropriate data
    cleaned_memo = ""  # Replace with cleaned memo data
    cleaned_name = ""  # Replace with cleaned name data

    updated_transaction_lines = swap_and_adjust(
        transaction_lines, cleaned_memo, cleaned_name
    )

    # Perform assertions based on your requirements
    # ...

if __name__ == "__main__":
    pytest.main()


"""