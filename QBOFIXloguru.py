# -*- coding: utf-8 -*-

""" qbo_updater / Modify Quickbooks bank downloads to improve importing accuracy
"""


# files to be updated
FILE_EXT = ".qbo"
DEFAULT_DOWNLOAD_FILENAME = "download.qbo"
BASE_DIRECTORY = "G:/Downloads/"
OUTPUT_DIRECTORY = "C:/Users/Conrad/Documents/"

# text to remove from transaction descriptions
BAD_TEXT = [r"DEBIT +\d{4}", "CKCD ", "AC-", "POS ", "POS DB ", "-ONLINE", "-ACH"]


import os
import re
import sys
import time
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
    QBO_FILE_DATE_TAG = "<DTEND>"
    ACCOUNT_NUMBER_TAG = "<ACCTID>"
    file_date, acct_number = "nodate", "nonumber"
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

    return (
        clean_file_lines[::-1],  # return lines in same order as submitted
        file_date,
        acct_number,
    )


@logger.catch
def process_QBO():
    # Run the processes since that seems to be the purpose
    while True:
        # loop until something to process is found
        logger.info("...checking download directory...")
        for name in list(QBO_DOWNLOAD_DIRECTORY.glob("*.js")):
            if name.endswith(".qbo"):
                print(name)
        file_pathobj = Path(QBO_DOWNLOAD_DIRECTORY, DEFAULT_DOWNLOAD_FILENAME)

        originalfile = read_base_file(file_pathobj)

        if originalfile == []:
            logger.info(f"File not yet found: {file_pathobj.name}")
            time.sleep(10)
        else:
            # we have a file, try to process
            result, file_date, acct_number = clean_qbo_file(originalfile, BAD_TEXT)

            # Attempt to write results to cleanfile
            fname = "".join([file_date, "_", acct_number, FILE_EXT])
            logger.info(f"Attempting to output to file name: {fname}")
            clean_output_file = Path(QBO_MODIFIED_DIRECTORY, fname)
            try:
                with open(clean_output_file, "w") as f:
                    f.writelines(result)
            except Exception as e:
                logger.error(f"Error in writing {clean_output_file}")
                logger.warning(str(e))
                sys.exit(1)

            logger.info(f"File {clean_output_file} contents written successfully.")

            logger.info(f"Attempting to remove old {file_pathobj} file...")

            if Path(file_pathobj).exists():
                try:
                    os.remove(file_pathobj)
                except OSError as e:
                    logger.warning(f"Error: {e.file_path} - {e.strerror}")
                    sys.exit(1)
                logger.info(f"Success removing {file_pathobj.name}")

            else:
                logger.info(f"Sorry, I can not find {file_pathobj.name} file.")

            # declare program end
            logger.info("Program End: nominal")
            sys.exit(0)
    return


@logger.catch
def defineLoggers(filename):
    class Rotator:
        # Custom rotation handler that combines filesize limits with time controlled rotation.
        def __init__(self, *, size, at):
            now = dt.datetime.now()
            self._size_limit = size
            self._time_limit = now.replace(hour=at.hour, minute=at.minute, second=at.second)
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
    rotator = Rotator(size=5e+8, at=dt.time(0, 0, 0))
    # example useage: logger.add("file.log", rotation=rotator.should_rotate)    

    # Begin logging definition
    logger.remove()  # removes the default console logger provided by Loguru.
    # I find it to be too noisy with details more appropriate for file logging.

    # INFO and messages of higher priority only shown on the console.
    # it uses the tqdm module .write method to allow tqdm to display correctly.
    logger.add(lambda msg: tqdm.write(msg, end=""), format="{message}", level="ERROR")

    logger.configure(handlers=[{"sink": os.sys.stderr, "level": "DEBUG"}])  
    # this method automatically suppresses the default handler to modify the message level

    logger.add(
        "".join(["./LOGS/", filename, "_{time}.log"]),
        rotation=rotator.should_rotate,
        level="DEBUG",
        encoding="utf8"
    )
    # create a new log file for each run of the program
    return


@logger.catch
def Main():
    defineLoggers(f"{RUNTIME_NAME}_{OS_FILENAME_SAFE_TIMESTR}")

    logger.info("Program Start.")  # log the start of the program

    process_QBO()

    logger.info("Program End.") 

    return


"""Check if this file is being run directly
"""
if __name__ == "__main__":
    Main()
