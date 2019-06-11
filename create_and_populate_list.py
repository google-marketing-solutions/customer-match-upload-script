#!/usr/bin/env python
#
# Copyright 2019 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Adds user lists and populates them with customer's CRM contact information.

Note: It may take several hours for the list to be populated with members. Email
addresses must be associated with a Google account. For privacy purposes, the
user list size will show as zero until the list has at least 1000 members. After
that, the size will be rounded to the two most significant digits.
"""

import argparse
import csv
import hashlib
import logging
import os
from googleads import adwords
import yaml

# CSV Headers (Change if needed)
HEADER_LINE = True
EMAIL = 'Email'
PHONE = 'Phone'
MOBILE_ID = 'MobileId'
USER_ID = 'UserId'
FIRST_NAME = 'FirstName'
LAST_NAME = 'LastName'
COUNTRY_CODE = 'CountryCode'
ZIP_CODE = 'ZipCode'
LIST_NAME = 'List'
IS_DATA_ENCRYPTED = True

# Default Values
GENERIC_LIST = 'Generic List from the API'
MAX_ITEMS_PER_CALL = 990
CSV_FILE_PATH = 'audience.csv'
CONFIG_PATH = './googleads_config.yaml'
MEMBERSHIP_LIFESPAN_DAYS = 8

logger = logging.getLogger('local')

parser = argparse.ArgumentParser(
    description='Uploads customer match list to Google Ads.')
parser.add_argument(
    '--config_file',
    default=CONFIG_PATH,
    help='Configuration file for Google Ads API access.')
parser.add_argument(
    '--audience_file',
    default=CSV_FILE_PATH,
    help='CSV file with audience list.')


def setup_logging(path='logging_config.yaml', level=logging.INFO):
  if os.path.exists(path):
    with open(path, 'rt') as f:
      config = yaml.safe_load(f.read())
    logging.config.dictConfig(config)
  else:
    logging.basicConfig(level=level)


def generate_list_data_base():
  data_base = {}
  data_base['emails'] = []
  data_base['phones'] = []
  data_base['mobile_ids'] = []
  data_base['user_ids'] = []
  data_base['addresses'] = []
  return data_base


def read_csv(path):
  """Reads customer data from CSV and stores it in memory.

  Args:
    path: CSV file path.

  Returns:
    customer_data: Processed data from CSV.
  """
  with open(path, mode='r') as csv_file:
    csv_reader = csv.DictReader(csv_file)
    line_count = 0

    customer_data = {}

    for row in csv_reader:
      if HEADER_LINE and line_count == 0:
        # Skip Header Line
        line_count += 1
        next

      if row.get(LIST_NAME):
        if not customer_data.get(row[LIST_NAME]):
          customer_data[row[LIST_NAME]] = generate_list_data_base()
        list_data = customer_data[row[LIST_NAME]]
      else:
        # Use generic list
        if not customer_data.get(GENERIC_LIST):
          customer_data[GENERIC_LIST] = generate_list_data_base()
        list_data = customer_data[GENERIC_LIST]

      if row.get(EMAIL):
        if IS_DATA_ENCRYPTED:
          list_data['emails'].append({'hashedEmail': row[EMAIL]})
        else:
          list_data['emails'].append(
              {'hashedEmail': normalize_and_sha256(row[EMAIL])})

      if row.get(PHONE):
        if IS_DATA_ENCRYPTED:
          list_data['phones'].append({'hashedPhoneNumber': row[PHONE]})
        else:
          list_data['phones'].append(
              {'hashedPhoneNumber': normalize_and_sha256(row[PHONE])})

      if row.get(MOBILE_ID):
        list_data['mobile_ids'].append({'mobileId': row[MOBILE_ID]})
      if row.get(USER_ID):
        list_data['user_ids'].append({'userId': row[USER_ID]})
      if (row.get(FIRST_NAME) and row.get(LAST_NAME) and
          row.get(COUNTRY_CODE) and row.get(ZIP_CODE)):
        address = {}
        if IS_DATA_ENCRYPTED:
          address['hashedFirstName'] = row[FIRST_NAME]
          address['hashedLastName'] = row[LAST_NAME]
        else:
          address['hashedFirstName'] = normalize_and_sha256(row[FIRST_NAME])
          address['hashedLastName'] = normalize_and_sha256(row[LAST_NAME])
        address['CountryCode'] = row[COUNTRY_CODE]
        address['ZipCode'] = row[ZIP_CODE]
        list_data['addresses'].append(address)
      line_count += 1

    logger.info('Processed %d lines from file %s.', line_count, path)

    return customer_data


def upload_data(client, list_name, customer_data):
  """Uploads processed data to the specified list and creates it if necessary.

  Args:
    client: Adwords API client used to create and mutate the user list.
    list_name: The name of the user list to modify.
    customer_data: Processed customer data to be uploaded.

  Returns:
    None.
  """
  # Initialize appropriate services.
  user_list_service = client.GetService('AdwordsUserListService', 'v201809')

  # Check if the list already exists
  selector = {
      'fields': ['Name', 'Id'],
      'predicates': [{
          'field': 'Name',
          'operator': 'EQUALS',
          'values': list_name
      }],
  }
  result = user_list_service.get(selector)
  if result['entries']:
    logger.info(
        'The user list %s is already created and its info was retrieved.',
        list_name)
    user_list_id = result['entries'][0]['id']
  else:
    logger.info('The user list %s will be created.', list_name)
    user_list = {
        'xsi_type': 'CrmBasedUserList',
        'name': list_name,
        'description': 'This is a list of users uploaded from Adwords API',
        # CRM-based user lists can use a membershipLifeSpan of 10000 to indicate
        # unlimited; otherwise normal values apply.
        'membershipLifeSpan': MEMBERSHIP_LIFESPAN_DAYS,
        'uploadKeyType': 'CONTACT_INFO'
    }

    # Create an operation to add the user list.
    operations = [{'operator': 'ADD', 'operand': user_list}]
    result = user_list_service.mutate(operations)
    user_list_id = result['value'][0]['id']

  members = []
  if customer_data['emails']:
    members.extend(customer_data['emails'])
  if customer_data['phones']:
    members.extend(customer_data['phones'])
  if customer_data['mobile_ids']:
    members.extend(customer_data['mobile_ids'])
  if customer_data['user_ids']:
    members.extend(customer_data['user_ids'])
  if customer_data['addresses']:
    members.extend(customer_data['addresses'])

  total_uploaded = 0
  # Flow control to keep calls within usage limits
  logger.info('Starting upload.')
  for i in range(0, len(members), MAX_ITEMS_PER_CALL):
    start = i
    end = i + MAX_ITEMS_PER_CALL

    members_to_upload = members[start:end]

    mutate_members_operation = {
        'operand': {
            'userListId': user_list_id,
            'membersList': members_to_upload
        },
        'operator': 'ADD'
    }

    response = user_list_service.mutateMembers([mutate_members_operation])

    if 'userLists' in response:
      for user_list in response['userLists']:
        logger.info(
            '%d members were added to user list with name "%s" & ID "%d".',
            len(members_to_upload), user_list['name'], user_list['id'])
      total_uploaded += len(members_to_upload)

  logger.info(
      'A total of %d members were added to user list with name "%s" & ID "%d".',
      total_uploaded, user_list['name'], user_list['id'])


def normalize_and_sha256(s):
  """Normalizes (lowercase, remove whitespace) and hashes a string with SHA-256.

  Args:
    s: The string to perform this operation on.

  Returns:
    A normalized and SHA-256 hashed string.
  """
  return hashlib.sha256(s.strip().lower()).hexdigest()


if __name__ == '__main__':
  # Initialize client object.
  setup_logging()
  logger.info('Starting the process.')
  args = parser.parse_args()
  adwords_client = adwords.AdWordsClient.LoadFromStorage(path=args.config_file)
  data = read_csv(args.audience_file)

  for name in data:
    upload_data(adwords_client, name, data[name])

  logger.info('Process has finished.')
