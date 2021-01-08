import requests
from selenium.webdriver.common.keys import Keys

import datetime
import csv
import logging
import os
import time

logging.getLogger('')


def get_address_name_number(formatted_address):
    address_arr = formatted_address.split()
    name, number = address_arr[0], address_arr[1]
    number = number.replace("(", "")
    number = number.replace(")", "")
    return name, number


def get_pdf_filepath(street_name, street_number, pdf_dir):
    now = datetime.datetime.now()
    filename = f'{street_name} ({street_number}) - Property Tax ({now.year - 1})'
    filename = filename.title()
    filepath = os.path.join(pdf_dir, filename + '.pdf')

    # append a character at the end of the filename if it exists already
    if os.path.isfile(filepath):
        ch = 'a'
        i = 0
        while True:
            suffix = chr(ord(ch) + i)
            temp_filename = filename + suffix
            temp_filepath = os.path.join(pdf_dir, temp_filename + '.pdf')
            if not os.path.isfile(temp_filepath):
                filename, filepath = temp_filename, temp_filepath
                break
            i += 1

    return filepath


def download(account_number, address, output_csv, pdf_dir, driver):
    """
    Retrieves property tax data from www.hctax.net for a given property, and downloads the relevant pdf statement.
    """

    street_name, street_number = get_address_name_number(address)

    # Pull up the site and start searching...
    driver.get('https://www.hctax.net/Property/PropertyTax')

    time.sleep(2)
    search_box = driver.find_element_by_id("txtSearchValue")
    search_box.send_keys(account_number)
    search_box.send_keys(Keys.ENTER)

    # TODO: Update this to wait until the jtable-data-row jtable-row-even table is loaded
    time.sleep(4)

    account_table_rows = driver.find_elements_by_class_name('jtable-data-row')
    matched = False
    # The account number can occasionally be missing leading zeroes, which can cause multiple matches.
    # To validate we are grabbing the right account we also search the table row for the address info.
    for tr in account_table_rows:
        matches = [account_number, street_name.upper(), street_number]
        if all(x in tr.text.upper() for x in matches):
            matched = True
            account_page = tr.find_element_by_partial_link_text(account_number)
            account_page.click()

    if not matched:
        logging.critical(f'Unable to find match for account {account_number} - skipping')
        return

    # TODO: Make proper wait for page to load
    time.sleep(2)

    print_button = driver.find_element_by_class_name('StatementPrint')

    # Find the tax amount
    table = driver.find_element_by_class_name('tot')

    tax_amount = 0
    for tax_row in table.find_elements_by_xpath(".//tr"):
        tax_amount = tax_row.text.split()[-1]
        break

    if not tax_amount:
        logging.critical(f'Failure retrieving tax amount for account {account_number}')
        return

    # Write the tax amount to second csv
    fields = [account_number, address, tax_amount]

    # TODO: This is making an extra newline between each entry, fix that.
    with open(output_csv, 'a') as t:
        mywriter = csv.writer(t)
        mywriter.writerow(fields)

    # Download the pdf
    fake_agent_header = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_4) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36",
    }

    data = requests.get(print_button.get_attribute('href'), headers=fake_agent_header)

    if data.status_code != 200:
        logging.error(
            f'Unable to download PDF report for account {account_number}\n{data.status_code}, {data.content}')

    pdf_filepath = get_pdf_filepath(street_name, street_number, pdf_dir)
    with open(pdf_filepath, 'wb') as output:
        output.write(data.content)

    return
