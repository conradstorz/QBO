# qbo_updater / Modify Quickbooks bank downloads to improve importing accuracy

# files to be updated
file_extension = ".qbo"
filename = "download.qbo"
# cleanfile = 'clean.qbo'
basedirectory = "./Downloads/"
outputdirectory = "./Documents/"

# text to remove from transaction descriptions
#bad_text = ["DEBIT +\d{4}", "CKCD DEBIT ", "AC-", "POS DEBIT ", "POS DB "]
bad_text = [r"DEBIT +\d{4}", "CKCD ", "AC-", "POS ", "POS DB "]
qbo_file_date_tag = "<DTEND>"
file_date = ""
acct_number_tag = "<ACCTID>"
acct_number = ""

import os
import re
import sys
import time
import logging

# establish logging state
FORMAT = "%(asctime)-15s %(clientip)s %(user)-8s %(message)s"
logging.basicConfig(format=FORMAT, level=logging.INFO)
d = {"clientip": "xxx.xxx.xxx.xxx", "user": "qbo_loggs"}
# logging.warning('Protocol problem: %s', 'connection reset', extra=d)

# declare program start
logging.info("Program Start: %s", "nominal", extra=d)


def read_base_file(base_file):
    """read_base_file(fully qualified filename)
    Return a list of lines contained in base_file.
    """
    try:
        with open(base_file) as f:
            file_contents = f.readlines()
    except Exception as e:
        logging.error("Error in reading %s", base_file, extra=d)
        logging.warning(str(e), extra=d)
        file_contents = []

    if file_contents != []:
        logging.debug(file_contents)
        logging.info("File contents read successfully.", extra=d)
    return file_contents


def Clean_Line(t, line):
    """Clean_Line(text to be removed, text to have modified)
    Return line with redundant spaces removed and text deleted if exists.
    """
    line = re.sub(r" +", " ", line)  # remove duplicate spaces from within line
    #return line.replace(t, "").lstrip()  # strip leading whitespace
    line = re.sub(t, "", line)
    return line.strip()


def clean_qbo_file(lines, text):
    """clean_qbo_file(list of lines, list of text strings to remove)
    Remove unwanted text from transaction data from bank download in quickbooks format.
    My bank provides poorly formatted data. Quickbooks loses access to data due to
    the fact that the memo line has a longer line length allowed by quickbooks.
    This function replaces the nametag with the cleaned memotag data.
    """
    global file_date, acct_number
    maximum_nametag_line_length = 32
    memotag = "<MEMO>"
    nametag = "<NAME>"
    name_line = "<ERROR>"
    clean_file_lines = []
    for line in lines[::-1]: # in reverse order [::-1] so we process memo before name lines
        logging.debug(line, extra=d)

        if line.startswith(qbo_file_date_tag):
            # extract file date for use with naming output file
            file_date = line.replace(qbo_file_date_tag, "").lstrip().rstrip()

        if line.startswith(acct_number_tag):
            # extract bank account number for use in naming output file
            acct_number = line.replace(acct_number_tag, "").lstrip().rstrip()

        if line.startswith(memotag):
            # memo lines contain the desired info about transactions
            # name lines are used by quickbooks to match transactions
            # discard less useful nametag information from bank after cleaning memo info
            line = line.replace(memotag, "").lstrip()  # remove memotag
            for t in text:
                # remove each occurance from line
                line = Clean_Line(t, line)
                logging.debug(line, extra=d)

            name_line = nametag + line[:maximum_nametag_line_length] + '\n'
            line = memotag + line + '\n'  # replace memotag

        if line.startswith(nametag):
            line = name_line  # replace nameline with memoline

        logging.debug(line, extra=d)
        clean_file_lines.append(line)

    return clean_file_lines[::-1]  # return lines in same order as submitted


"""Check if this file is being run directly
"""
if __name__ == "__main__":
    # Run the processes since that seems to be the purpose
    while True:
        # loop until something to process is found
        logging.info("...checking download directory...", extra=d)
        for name in os.listdir(basedirectory):
            if name.endswith(".qbo"):
                print(name)
        file_path = os.path.join(basedirectory, filename)

        originalfile = read_base_file(file_path)

        if originalfile == []:
            logging.info("File not yet found %s" % file_path, extra=d)
            time.sleep(10)
        else:
            # we have a file, try to process
            result = clean_qbo_file(originalfile, bad_text)

            # Attempt to write results to cleanfile
            cf = outputdirectory + file_date + "_" + acct_number + file_extension
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
