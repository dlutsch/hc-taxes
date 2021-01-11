from downloader import download
import PySimpleGUI as sg
from selenium import webdriver

import csv
import logging
import os

log_buffer = ''


def get_output_filepath(input_filepath):
    """
    Creates the output csv filepath for a given input filepath.
    Output should be the same as input, but with a _taxes suffix before the file extension.
    """
    dir, file = os.path.split(input_filepath)
    splitext = os.path.splitext(file)
    output_filename = splitext[0] + "_taxes" + splitext[1]
    output_filepath = os.path.join(dir, output_filename)
    return output_filepath


def init_selenium(chromedriver_path, headless=False):
    # Selenium config
    options = webdriver.ChromeOptions()
    if headless:
        options.add_argument('headless')
    return webdriver.Chrome(executable_path=chromedriver_path, options=options)


def init_gui():
    sg.theme('Dark Blue 3')

    layout = [
        [sg.Text('Input CSV', size=(10, 1)), sg.Input(key='-INPUT-', change_submits=True),
         sg.FileBrowse(key='-INPUT_BROWSE-', file_types=(("CSV Files", "*.csv"),))],
        [sg.Text('PDF Output', size=(10, 1)), sg.Input(key='-PDF_DIR-', change_submits=True),
         sg.FolderBrowse(key='-INPUT_BROWSE-')],
        [sg.Text('Chromedriver', size=(10, 1)), sg.Input(key='-DRIVER-', change_submits=True),
         sg.FileBrowse(key='-DRIVER_BROWSE-', file_types=(("EXE Files", "*.exe"),))],
        [sg.Text('Run in Background', size=(15, 1)), sg.Radio('True', "BGRADIO", default=True, key='-HEADLESS-'),
         sg.Radio('False', "BGRADIO")],
        [sg.MLine(key='-OUTPUT-' + sg.WRITE_ONLY_KEY, size=(70, 20))],
        [sg.OK(), sg.Cancel()]
    ]
    # Testing
    # layout = [
    #     [sg.Text('Input CSV', size=(10, 1)), sg.Input(default_text='/Users/dlutsch/Desktop/sample2.csv', key='-INPUT-', change_submits=True),
    #      sg.FileBrowse(key='-INPUT_BROWSE-', file_types=(("CSV Files", "*.csv"),))],
    #     [sg.Text('PDF Output', size=(10, 1)), sg.Input(default_text='/Users/dlutsch/Desktop/pdf', key='-PDF_DIR-', change_submits=True),
    #      sg.FolderBrowse(key='-INPUT_BROWSE-')],
    #     [sg.Text('Chromedriver', size=(10, 1)), sg.Input(default_text='/Users/dlutsch/chromedriver',key='-DRIVER-', change_submits=True),
    #      sg.FileBrowse(key='-DRIVER_BROWSE-', file_types=(("EXE Files", "*.exe"),))],
    #     [sg.Text('Run in Background', size=(15, 1)), sg.Radio('True', "BGRADIO", default=True, key='-HEADLESS-'),
    #      sg.Radio('False', "BGRADIO")],
    #     [sg.MLine(key='-OUTPUT-' + sg.WRITE_ONLY_KEY, size=(70, 20))],
    #     [sg.OK(), sg.Cancel()]
    # ]

    return sg.Window('Harris County Property Tax Downloader', layout)


class Handler(logging.StreamHandler):

    def __init__(self):
        logging.StreamHandler.__init__(self)

    def emit(self, record):
        global log_buffer
        if record.levelname != 'INFO':
            record = f'[{record.levelname}] {record.message}'
        else:
            record = record.message
        log_buffer = f'{log_buffer}\n{str(record)}'.strip()
        window['-OUTPUT-' + sg.WRITE_ONLY_KEY].update(value=log_buffer)
        window.Refresh()


def config_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s, [%(levelname)s], %(message)s',
        filename='hc-proptax.log',
        filemode='w')

    ch = Handler()
    ch.setLevel(logging.INFO)
    logging.getLogger('').addHandler(ch)


if __name__ == '__main__':

    window = init_gui()

    while True:  # Event Loop
        event, values = window.read()
        if event == sg.WIN_CLOSED or event == 'Cancel':
            break
        if event == 'OK':
            driver = init_selenium(values['-DRIVER-'], values['-HEADLESS-'])
            pdf_dir = values['-PDF_DIR-']
            window['-OUTPUT-' + sg.WRITE_ONLY_KEY].update("")
            output_file = get_output_filepath(values['-INPUT-'])
            config_logging()
            logging.info(f'OUTPUT FILE: {output_file}')
            window.Refresh()

            with open(values['-INPUT-'], 'rt') as f:
                reader = csv.reader(f)
                row_count = sum(1 for row in reader)
                f.seek(0)
                progress = 0
                sg.OneLineProgressMeter('Download Progress', progress, row_count, 'dl')
                for row in reader:
                    try:
                        account_number, _, address = row[0], row[1], row[2]
                    except IndexError:
                        logging.critical('malformed csv file')
                        sg.OneLineProgressMeter('Download Progress', row_count, row_count, 'dl')
                        break
                    if account_number:
                        progress += 1
                        logging.info(f'Retrieving data for: {account_number}...')
                        download(account_number, address, output_file, pdf_dir, driver)
                        sg.OneLineProgressMeter('Download Progress', progress, row_count, 'dl')

            if progress:
                logging.info('Download complete!')

    window.close()
