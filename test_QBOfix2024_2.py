# test_preprocess_memo.py

import re
from hypothesis import given, strategies as st
import pytest
from loguru import logger


from QBOfix2024_2 import preprocess_memo, BAD_TEXT

# Let's run some pytest tests...
# TODO need to test regex pattern
def test_removal_of_bad_text_patterns():
    assert preprocess_memo("DEBIT Some Transaction") == "Some Transaction"
    assert preprocess_memo("CKCD Transaction") == "Transaction"
    # Add more tests for each pattern

def test_shortening_common_phrases():
    assert preprocess_memo("BILL PAYMT for Utilities") == "BillPay for Utilities"

def test_cleanup_of_spacing():
    assert preprocess_memo("Transaction  with  extra  spaces") == "Transaction with extra spaces"


# let's launch hypothesis now...
@given(st.text())
def test_hypothesis_with_random_text(input_str):
    # Hypothesis will generate random strings, including empty and special characters
    result = preprocess_memo(input_str)
    # You can assert general properties about the result here, for example:
    # Result should not contain any BAD_TEXT patterns
    for bad_text in BAD_TEXT:
        assert re.search(bad_text, result) is None
    # Result should not have multiple consecutive spaces
    assert not re.search(r'  +', result)
    # Add more assertions based on what your function should guarantee about the output

from hypothesis import given, strategies as st

@given(st.text(alphabet=st.characters(blacklist_characters="abcdefghijklmnopqrstuvwxyz", whitelist_categories=('P', 'Z')), min_size=1))
def test_preprocess_memo_special_characters(input_str):
    # This test focuses on input strings with special characters and potentially problematic characters
    result = preprocess_memo(input_str)
    # Assertions to check the result meets expectations
    assert not any(bad_text in result for bad_text in BAD_TEXT)
    assert "  " not in result, "There should not be consecutive spaces"
    # Add more specific assertions here

from hypothesis.strategies import composite

@composite
def memo_text(draw, text=st.text(min_size=1)):
    # Generate a base text
    base_text = draw(text)
    # Optionally add a bad pattern
    bad_text = draw(st.sampled_from(BAD_TEXT))
    # Create a new text by inserting the bad pattern into the base text
    new_text = base_text + bad_text + base_text
    return new_text

@given(memo_text())
def test_composite_preprocess_memo(input_str):
    result = preprocess_memo(input_str)
    assert not any(bad_text in result for bad_text in BAD_TEXT), "No bad text should remain"


from QBOfix2024_2 import extract_transaction_details  # Adjust the import as necessary

def test_basic_functionality():
    input_lines = ["<tag1>value1", "<tag2>value2"]
    expected = {"tag1": "value1", "tag2": "value2"}
    assert extract_transaction_details(input_lines) == expected

def test_incorrect_format():
    input_lines = ["tag1>value1", "<tag2value2"]
    expected = {}  # Assuming incorrect formats are ignored
    assert extract_transaction_details(input_lines) == expected

def test_empty_input():
    input_lines = []
    expected = {}
    assert extract_transaction_details(input_lines) == expected

def test_lines_with_no_tags_or_values():
    input_lines = ["<>", "<tag>"]
    expected = {"": "", "tag": ""}
    assert extract_transaction_details(input_lines) == expected


from hypothesis import given, strategies as st

@given(st.lists(st.text()))
def test_hypothesis_random_strings(input_lines):
    # Hypothesis will generate random lists of strings
    result = extract_transaction_details(input_lines)
    # Basic assertion: result should be a dictionary
    assert isinstance(result, dict)
    # You can add more detailed assertions based on the properties of your function's output
"""
# not ready yet
@given(st.lists(st.text(min_size=3).map(lambda x: f"<{x}>"), min_size=1))
def test_hypothesis_well_formatted_strings(input_lines):
    result = extract_transaction_details(input_lines)
    # Every item in input_lines should result in an entry in the dictionary, even if the value is empty
    assert len(result) == len(input_lines)
    # Check that keys are correctly extracted without leading '<'
    for line in input_lines:
        tag = line[1:line.find(">")]  # Extract tag from formatted string
        assert tag in result
"""

from QBOfix2024_2 import process_transaction  # Adjust the import as necessary

def test_memo_presence_and_name_memo_swap():
    transaction_lines = ["<NAME>John Doe"]
    processed_lines = process_transaction(transaction_lines)
    # After processing, there should be a default memo, and then NAME and MEMO are swapped
    # So, we check if MEMO now equals "John Doe" after the swap
    assert any("<MEMO>John Doe" in line for line in processed_lines), "MEMO should equal 'John Doe' after swap"
    assert any("<NAME>No Memo" in line for line in processed_lines), "NAME should equal 'No Memo' after swap"

def test_memo_preprocessing_and_name_memo_swap():
    transaction_lines = ["<NAME>John Doe", "<MEMO>CKCD Shopping"]
    result = process_transaction(transaction_lines)
    # Assuming preprocess_memo and truncate_name are correctly removing "CKCD " and truncating as necessary
    assert any("<MEMO>John Doe" in line for line in result)  # Swapped
    # Further assertions depending on the specifics of preprocess_memo and truncate_name

def test_name_memo_check_paid():
    transaction_lines = ["<NAME>CHECK PAID", "<MEMO>CHECK PAID", "<CHECKNUM>123", "<REFNUM>456"]
    result = process_transaction(transaction_lines)
    assert any("<NAME>123" in line for line in result)
    assert any("<MEMO>456" in line for line in result)

def test_output_format():
    transaction_lines = ["<NAME>John Doe", "<MEMO>Online Purchase"]
    result = process_transaction(transaction_lines)
    assert isinstance(result, list)
    assert all(line.startswith("<") and line.endswith("\n") for line in result)


from hypothesis import given, strategies as st

@given(st.lists(st.text(min_size=1), min_size=1))
def test_process_transaction_with_random_input(transaction_lines):
    # This will generate lists of random text strings
    result = process_transaction(transaction_lines)
    # Basic checks to ensure result integrity
    assert isinstance(result, list)
    assert all(line.startswith("<") and line.endswith("\n") for line in result)
    # Depending on what extract_transaction_details and preprocess_memo do, you might add:
    # - Assertions to check for the presence of expected tags
    # - Assertions to ensure no unexpected modifications to certain tag values
