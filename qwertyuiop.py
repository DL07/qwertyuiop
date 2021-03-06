#!/usr/bin/env python
import os.path
import argparse
import pandas as pd
import time
import configparser
import os
import string
import itertools
import argparse
import random
import re
import logging
import multiprocessing as mp

logging.basicConfig(level=logging.INFO, format='%(message)s')

CONFIG_FILE = 'config.ini'
RANDOM_PASSWORD_LENGTH = 10

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", dest="pwdfile", required=True, default="password.txt",
                        help="File containing passwords to test")
    parser.add_argument("-b", "--benchmark",
                        help="Perform benchmark and use number of threads")
    parser.add_argument("-o", "--output", required= True, default="output.csv",
                        help="Filename to output to csv")

    args = parser.parse_args()

    # create config file if it doesn't exist
    if not(os.path.isfile(CONFIG_FILE)):
        create_config_file()
    else:
        if(args.benchmark):
            parallel_brute_force(int(args.benchmark))

    guess_rate = int(get_guess_rate())
    logging.info('Guess rate per second: {}'.format(guess_rate))

    # init lists for csv output
    passwords = []
    crack_hours = []
    crack_days = []
    permutations = []

    # run through passwords file
    with open(args.pwdfile) as pf:
        logging.info('Analysing {}'.format(args.pwdfile))
        password = pf.readline().strip()
        while password:
            sample_space = get_search_space(password)
            total_search_space = sample_space**len(password)
            crack_time_hours = (total_search_space / guess_rate) / 60 / 60
            crack_time_days = crack_time_hours / 24

            passwords.append(password.strip())
            crack_hours.append('{:.2f}'.format(crack_time_hours))
            crack_days.append('{:.2f}'.format(crack_time_days))
            permutations.append('{}^{}'.format(sample_space, len(password)))

            password = pf.readline().strip()
    logging.info('Finished analysis.')

    # create dataframe and output csv
    df_data = {'Password':passwords,
                'Crack Time H': crack_hours,
                'Crack Time D':crack_days,
                'Permutations':permutations}
    df = pd.DataFrame(df_data)
    df.to_csv(args.output, index = False)
    logging.info('Output saved to: {}'.format(args.output))

def get_guess_rate():
    if not(os.path.isfile(CONFIG_FILE)):
        logging.warning('Config file not found.')
        create_config_file()

    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)

    guess_rate = config.get('benchmark_settings', 'guess_rate')
    return guess_rate

def get_benchmark_guesses():
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)

    guess_limit = config.get('benchmark_settings', 'benchmark_guesses')
    return guess_limit

def get_search_space(password):
    search_space = 0
    alphabet_length = 26
    digits_length = 10
    punctuation_length = 33

    lowercase_re = re.compile("[a-z]")
    uppercase_re = re.compile("[A-Z]")
    digits_re = re.compile("[0-9]")
    punc_re = re.compile(r"\W")

    if(lowercase_re.search(password)):
        search_space = search_space + alphabet_length

    if(uppercase_re.search(password)):
        search_space = search_space + alphabet_length

    if(digits_re.search(password)):
        search_space = search_space + digits_length

    if(punc_re.search(password)):
        search_space = search_space + punctuation_length

    return search_space

def brute_force(guess_limit, alpha_chunk, random_password):
    guesses = 0
    for guess in itertools.product(alpha_chunk, repeat=len(random_password)):
        guesses += 1
        if(''.join(guess) == random_password):
            logging.info('Found password: {}'.format(''.join(guess)))
            break
        if(guesses == guess_limit): break

def parallel_brute_force(thread_count):
    # split alphabet into 4
    # assign 4 threads to cycle a portion of the alphabet search
    # return guess rate for each thread
    # add up for a total guess guess rate
    random_password = create_random_password()
    alphabet = string.ascii_letters + string.digits + string.punctuation
    benchmark_guesses = int(get_benchmark_guesses())
    thread_guess_limit = benchmark_guesses / thread_count
    chunk_size = len(alphabet) // thread_count # divide alphabet into 4
    pool = mp.Pool(processes=thread_count) # create 4 processes

    logging.info('Performing brute force benchmark...')
    time_start = time.time()

    for i in range(thread_count):
        if i == thread_count - 1:
            # if on last thread, chunk is from here to the end of alphabet
            chunk = alphabet[chunk_size * i :]
        else:
            # portion is this portion to the next
            # eg.
            chunk = alphabet[chunk_size * i : chunk_size * (i+1)]

        pool.apply_async(brute_force, args=(thread_guess_limit, chunk, random_password))

    pool.close()
    pool.join() # wait for all threads to finish

    time_finish = time.time()
    time_taken = time_finish - time_start # calculate time taken

    update_config_file('{:.0f}'.format(benchmark_guesses/time_taken))

    print('Multi-threaded brute force benchmark complete. Time taken: {:.2f}'.format(time_taken))

def create_random_password():
    random_password = ''.join([random.choice(string.ascii_letters + string.digits + string.punctuation) for n in range(RANDOM_PASSWORD_LENGTH)])
    return random_password

def create_config_file():
    logging.info('Creating config file: {}'.format(CONFIG_FILE))
    config = configparser.ConfigParser()
    config.add_section('benchmark_settings')
    config.set('benchmark_settings', 'guess_rate', str(0)) # default value
    config.set('benchmark_settings', 'benchmark_guesses', str(10000000)) # default value - 10 mil

    with open(CONFIG_FILE, "w") as f:
        config.write(f)

    logging.debug('Created file: {}'.format(CONFIG_FILE))

    parallel_brute_force(4)

def update_config_file(guess_rate):
    logging.debug('Updating guess rate...')
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)

    config.set('benchmark_settings', 'guess_rate', str(guess_rate))

    with open(CONFIG_FILE, "w") as f:
        config.write(f)

    logging.debug('Guess rate updated.')

if __name__ == '__main__':
    main()
