#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" qbo_updater / Modify Quickbooks bank downloads to improve importing accuracy
"""


# files to be updated
FILE_EXT = ".qbo"
DEFAULT_DOWNLOAD_FILENAME = "download.qbo"
BASE_DIRECTORY = "C:/Users/Conrad/Downloads/"
OUTPUT_DIRECTORY = "C:/Users/Conrad/Documents/"

# text to remove from transaction descriptions
BAD_TEXT = [r"DEBIT +\d{4}", "CKCD ", "AC-", "POS ", "POS DB "]

QBO_FILE_DATE_TAG = "<DTEND>"
file_date = ""
ACCOUNT_NUMBER_TAG = "<ACCTID>"
acct_number = ""

import os
import re
import sys
import time
from loguru import logger

RUNTIME_NAME = os.path.basename(__file__)


@logger.catch
def read_base_file(base_file):
    """read_base_file(fully qualified filename)
    Return a list of lines contained in base_file.
    """
    try:
        with open(base_file) as IN_FILE:
            file_contents = IN_FILE.readlines()
    except Exception as e:
        logger.error("Error in reading %s", base_file)
        logger.warning(str(e))
        file_contents = []

    if file_contents != []:
        logger.debug(file_contents)
        logger.info("File contents read successfully.")
    return file_contents


@logger.catch
def Clean_Line(t, line):
    """Clean_Line(text to be removed, text to have modified)
    Return line with redundant spaces removed and text deleted if exists.
    """
    line = re.sub(r" +", " ", line)  # remove duplicate spaces from within line
    # return line.replace(t, "").lstrip()  # strip leading whitespace
    line = re.sub(t, "", line)
    return line.strip()


@logger.catch
def clean_qbo_file(lines, text):
    """clean_qbo_file(list of lines, list of text strings to remove)
    Remove unwanted text from transaction data from bank download in quickbooks format.
    My bank provides poorly formatted data. Quickbooks loses access to data due to
    the fact that the memo line has a longer line length allowed by quickbooks.
    This function replaces the nametag with the cleaned memotag data.
    """
    global file_date, acct_number
    maximum_nametag_line_length = 32
    MEMO_TAG = "<MEMO>"
    NAME_TAG = "<NAME>"
    name_line = "<ERROR>"
    backupname = "<MEMO>"
    clean_file_lines = []
    for current_line in lines[::-1]:
        # in reverse order [::-1] so we process memo before name lines
        logger.debug(current_line)
        if current_line.startswith(NAME_TAG):
            backupname = current_line  # just in case there is no memo line

        if current_line.startswith(QBO_FILE_DATE_TAG):
            # extract file date for use with naming output file
            file_date = current_line.replace(QBO_FILE_DATE_TAG, "").lstrip().rstrip()

        if current_line.startswith(ACCOUNT_NUMBER_TAG):
            # extract bank account number for use in naming output file
            acct_number = current_line.replace(ACCOUNT_NUMBER_TAG, "").lstrip().rstrip()

        if current_line.startswith(MEMO_TAG):
            # memo lines contain the desired info about transactions
            # name lines are used by quickbooks to match transactions
            # discard less useful nametag information from bank after cleaning memo info
            current_line = current_line.replace(MEMO_TAG, "").lstrip()  # remove memotag
            for t in text:
                # remove each occurance from line
                current_line = Clean_Line(t, current_line)
                logger.debug(current_line)

            name_line = NAME_TAG + current_line[:maximum_nametag_line_length] + "\n"
            current_line = MEMO_TAG + current_line + "\n"  # replace memotag

        if current_line.startswith(NAME_TAG):
            current_line = name_line  # replace nameline with memoline

        logger.debug(current_line)
        if current_line == "<ERROR>":  # there was no memo line
            logger.info("there was no MEMO line for the current entry.")
            current_line = backupname  # so restore the original contents
            logger.debug(backupname + " ...restored")
        clean_file_lines.append(current_line)

    return clean_file_lines[::-1]  # return lines in same order as submitted


@logger.catch
def process_QBO():
    # Run the processes since that seems to be the purpose
    while True:
        # loop until something to process is found
        logger.info("...checking download directory...")
        for name in os.listdir(BASE_DIRECTORY):
            if name.endswith(".qbo"):
                print(name)
        file_path = os.path.join(BASE_DIRECTORY, DEFAULT_DOWNLOAD_FILENAME)

        originalfile = read_base_file(file_path)

        if originalfile == []:
            logger.info("File not yet found %s" % file_path)
            time.sleep(10)
        else:
            # we have a file, try to process
            result = clean_qbo_file(originalfile, BAD_TEXT)

            # Attempt to write results to cleanfile
            cf = OUTPUT_DIRECTORY + file_date + "_" + acct_number + FILE_EXT
            try:
                with open(cf, "w") as f:
                    f.writelines(result)
            except Exception as e:
                logger.error("Error in writing %s", cf)
                logger.warning(str(e))
                sys.exit(1)

            logger.info("File %s contents written successfully." % cf)

            logger.info("Attempting to remove old %s file..." % file_path)

            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except OSError as e:
                    logger.warning("Error: %s - %s." % (e.file_path, e.strerror))
                    sys.exit(1)
                logger.info("Success removing %s" % file_path)

            else:
                logger.info("Sorry, I can not find %s file." % file_path)

            # declare program end
            logger.info("Program End: %s", "nominal")
            sys.exit(0)
    return


@logger.catch
def Main():
    logger.configure(
        handlers=[{"sink": os.sys.stderr, "level": "INFO"}]
    )  # this method automatically suppresses the default handler to modify the message level

    #logfile_name = f'./LOGS/{runtime_name}_{time}.log'
    logger.add(  # create a new log file for each run of the program
        './LOGS/' + RUNTIME_NAME + '_{time}.log', level="INFO"
    )

    logger.info("Program Start.")  # log the start of the program

    process_QBO()
    return


"""Check if this file is being run directly
"""
if __name__ == "__main__":
    Main()
