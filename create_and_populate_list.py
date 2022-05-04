#!/usr/bin/env python
# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
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

from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException
from google.ads.googleads.v10.enums.types import customer_match_upload_key_type
from google.ads.googleads.v10.enums.types import offline_user_data_job_status
from google.ads.googleads.v10.enums.types import offline_user_data_job_type

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

# Default Values
GENERIC_LIST = 'Generic List from the API'
CSV_FILE_PATH = 'audience.csv'
CONFIG_PATH = './googleads_config.yaml'
MEMBERSHIP_LIFESPAN_DAYS = 8

# Constants
CONTACT_INFO = 'CONTACT_INFO'
MOBILE_ADVERTISING_ID = 'MOBILE_ADVERTISING_ID'
CRM_ID = 'CRM_ID'


def generate_list_data_base(list_type):
  """Generates an empty customer list data object.

  Args:
    list_type: The type of customer list (based on CustomerMatchUploadKeyType).

  Returns:
    data_base: an empty customer list data object.
  """
  data_base = {}
  if list_type == CONTACT_INFO:
    data_base['emails'] = []
    data_base['phones'] = []
    data_base['addresses'] = []
  elif list_type == MOBILE_ADVERTISING_ID:
    data_base['mobile_ids'] = []
  elif list_type == CRM_ID:
    data_base['user_ids'] = []
  return data_base


def is_list_empty(customer_data):
  if customer_data:
    for item in customer_data:
      if customer_data[item]:
        return False
  return True


def read_csv(path, list_type, hash_required):
  """Reads customer data from CSV and stores it in memory.

  Args:
    path: CSV file path.
    list_type: The type of customer list (based on CustomerMatchUploadKeyType).
    hash_required: Indicates if the customer data needs to be hashed.

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
        next  # pylint: disable=pointless-statement

      if row.get(LIST_NAME):
        if not customer_data.get(row[LIST_NAME]):
          customer_data[row[LIST_NAME]] = generate_list_data_base(list_type)
        list_data = customer_data[row[LIST_NAME]]
      else:
        # Use generic list
        if not customer_data.get(GENERIC_LIST):
          customer_data[GENERIC_LIST] = generate_list_data_base(list_type)
        list_data = customer_data[GENERIC_LIST]
      if list_type == CONTACT_INFO:
        if row.get(EMAIL):
          if hash_required:
            list_data['emails'].append(
                {'hashed_email': normalize_and_sha256(row[EMAIL])})
          else:
            list_data['emails'].append({'hashed_email': row[EMAIL]})

        if row.get(PHONE):
          if hash_required:
            list_data['phones'].append(
                {'hashed_phone_number': normalize_and_sha256(row[PHONE])})
          else:
            list_data['phones'].append({'hashed_phone_number': row[PHONE]})

        if (row.get(FIRST_NAME) and row.get(LAST_NAME) and
            row.get(COUNTRY_CODE) and row.get(ZIP_CODE)):
          address = {}
          if hash_required:
            address['hashed_first_name'] = normalize_and_sha256(row[FIRST_NAME])
            address['hashed_last_name'] = normalize_and_sha256(row[LAST_NAME])
          else:
            address['hashed_first_name'] = row[FIRST_NAME]
            address['hashed_last_name'] = row[LAST_NAME]
          address['country_code'] = row[COUNTRY_CODE]
          address['zip_code'] = row[ZIP_CODE]
          list_data['addresses'].append(address)

      elif list_type == MOBILE_ADVERTISING_ID:
        if row.get(MOBILE_ID):
          list_data['mobile_ids'].append({'mobile_id': row[MOBILE_ID]})

      elif list_type == CRM_ID:
        if row.get(USER_ID):
          list_data['user_ids'].append({'third_party_user_id': row[USER_ID]})
      line_count += 1

    print(f'Processed {line_count} lines from file {path}.')

    return customer_data


def get_user_list_resource_name(client, customer_id, list_name):
  """Gets the User List using the name provided.

  Args:
    client: The Google Ads client instance.
    customer_id: The customer ID for which to add the user list.
    list_name: The name of the user list to search.

  Returns:
    The User List resource name.
  """
  googleads_service_client = client.get_service('GoogleAdsService')
  query = f'''
      SELECT
        user_list.id,
        user_list.name
      FROM user_list
      WHERE user_list.name = '{list_name}'
      '''

  search_results = googleads_service_client.search(
      customer_id=customer_id, query=query)

  user_list_resource_name = None
  for result in search_results:
    user_list_resource_name = result.user_list.resource_name

  return user_list_resource_name


def create_user_list(client, customer_id, list_name, list_type, app_id=None):
  """Creates a User List using the name provided.

  Args:
    client: The Google Ads client instance.
    customer_id: The customer ID for which to add the user list.
    list_name: The name of the user list to search.
    list_type: The type of customer list (based on CustomerMatchUploadKeyType).
    app_id: App ID required only for mobile advertising lists.

  Returns:
    The User List resource name.
  """
  print(f'The user list {list_name} will be created.')
  user_list_service_client = client.get_service('UserListService')
  user_list_operation = client.get_type('UserListOperation')

  # Creates the new user list.
  user_list = user_list_operation.create
  user_list.name = list_name
  user_list.description = ('This is a list of users uploaded using Ads API.')
  user_list.crm_based_user_list.upload_key_type = (
    customer_match_upload_key_type.CustomerMatchUploadKeyTypeEnum.CustomerMatchUploadKeyType[
      list_type])
  if list_type == MOBILE_ADVERTISING_ID:
    user_list.crm_based_user_list.app_id = app_id

  user_list.membership_life_span = MEMBERSHIP_LIFESPAN_DAYS

  response = user_list_service_client.mutate_user_lists(
      customer_id=customer_id, operations=[user_list_operation])
  user_list_resource_name = response.results[0].resource_name
  print(
      f'User list with resource name "{user_list_resource_name}" was created.')
  return user_list_resource_name


def add_users_to_customer_match_user_list(client, customer_id,
                                          user_list_resource_name,
                                          customer_data, skip_polling):
  """Uses Customer Match to create and add users to a new user list.

  Args:
    client: The Google Ads client.
    customer_id: The customer ID for which to add the user list.
    user_list_resource_name: The resource name of the user list to which to
        add users.
    customer_data: Processed customer data to be uploaded.
    skip_polling: A bool dictating whether to poll the API for completion.
  """

  offline_user_data_job_service_client = client.get_service(
      'OfflineUserDataJobService')

  offline_user_data_job = client.get_type('OfflineUserDataJob')
  offline_user_data_job.type_ = client.get_type(
      'OfflineUserDataJobTypeEnum'
  ).OfflineUserDataJobType.CUSTOMER_MATCH_USER_LIST
  offline_user_data_job.customer_match_user_list_metadata.user_list = (
      user_list_resource_name)

  # Issues a request to create an offline user data job.
  create_offline_user_data_job_response = (
      offline_user_data_job_service_client.create_offline_user_data_job(
          customer_id=customer_id, job=offline_user_data_job))
  offline_user_data_job_resource_name = (
      create_offline_user_data_job_response.resource_name)
  print('Created an offline user data job with resource name: '
        f'"{offline_user_data_job_resource_name}".')

  request = client.get_type('AddOfflineUserDataJobOperationsRequest')
  request.resource_name = offline_user_data_job_resource_name
  request.operations.extend(build_offline_user_data_job_operations(
      client, customer_data))
  request.enable_partial_failure = True

  # Issues a request to add the operations to the offline user data job.
  response = offline_user_data_job_service_client.add_offline_user_data_job_operations(
      request=request)

  # Prints the status message if any partial failure error is returned.
  # Note: the details of each partial failure error are not printed here.
  # Refer to the error_handling/handle_partial_failure.py example to learn
  # more.
  # Extracts the partial failure from the response status.
  partial_failure = getattr(response, 'partial_failure_error', None)
  if getattr(partial_failure, 'code', None) != 0:
    error_details = getattr(partial_failure, 'details', [])
    for error_detail in error_details:
      failure_message = client.get_type('GoogleAdsFailure')
      # Retrieve the class definition of the GoogleAdsFailure instance
      # in order to use the "deserialize" class method to parse the
      # error_detail string into a protobuf message object.
      failure_object = type(failure_message).deserialize(error_detail.value)

      for error in failure_object.errors:
        print('A partial failure at index '
              f'{error.location.field_path_elements[0].index} occurred.\n'
              f'Error message: {error.message}\n'
              f'Error code: {error.error_code}')

  print('The operations are added to the offline user data job.')

  # Issues a request to run the offline user data job for executing all
  # added operations.
  operation_response = (
      offline_user_data_job_service_client.run_offline_user_data_job(
          resource_name=offline_user_data_job_resource_name))

  if skip_polling:
    check_job_status(
        client,
        customer_id,
        offline_user_data_job_resource_name,
        user_list_resource_name,
    )
  else:
    # Wait until the operation has finished.
    print('Request to execute the added operations started.')
    print('Waiting until operation completes...')
    operation_response.result()
    print_customer_match_user_list_info(client, customer_id,
                                        user_list_resource_name)


def build_offline_user_data_job_operations(client, customer_data):
  """Builds the schema of user data as defined in the API.

  Args:
    client: The Google Ads client.
    customer_data: Processed customer data to be uploaded.

  Returns:
    A list containing the operations.
  """

  customer_data_operations = []

  for data_type in customer_data:
    for item in customer_data[data_type]:
      # Creates a first user data based on an email address.
      user_data_operation = client.get_type('OfflineUserDataJobOperation')
      user_data = user_data_operation.create
      user_identifier = client.get_type('UserIdentifier')

      if data_type == 'emails':
        user_identifier.hashed_email = item['hashed_email']
      elif data_type == 'phones':
        user_identifier.hashed_phone_number = item['hashed_phone_number']
      elif data_type == 'mobile_ids':
        user_identifier.mobile_id = item['mobile_id']
      elif data_type == 'user_ids':
        user_identifier.third_party_user_id = item['third_party_user_id']
      elif data_type == 'addresses':
        user_identifier.address_info.hashed_first_name = item[
            'hashed_first_name']
        user_identifier.address_info.hashed_last_name = item['hashed_last_name']
        user_identifier.address_info.country_code = item['country_code']
        user_identifier.address_info.postal_code = item['postal_code']
      user_data.user_identifiers.append(user_identifier)

      customer_data_operations.append(user_data_operation)

  return customer_data_operations


def check_job_status(
    client,
    customer_id,
    offline_user_data_job_resource_name,
    user_list_resource_name,
):
  """Retrieves, checks, and prints the status of the offline user data job.

  Args:
    client: The Google Ads client.
    customer_id: The customer ID for which to add the user list.
    offline_user_data_job_resource_name: The resource name of the offline
        user data job to get the status of.
    user_list_resource_name: The resource name of the customer match user
        list
  """
  query = f'''
        SELECT
          offline_user_data_job.resource_name,
          offline_user_data_job.id,
          offline_user_data_job.status,
          offline_user_data_job.type,
          offline_user_data_job.failure_reason
        FROM offline_user_data_job
        WHERE offline_user_data_job.resource_name =
          '{offline_user_data_job_resource_name}'
        LIMIT 1'''

  # Issues a search request using streaming.
  google_ads_service = client.get_service('GoogleAdsService')
  results = google_ads_service.search(customer_id=customer_id, query=query)
  offline_user_data_job = next(iter(results)).offline_user_data_job
  job_type = offline_user_data_job_type.OfflineUserDataJobTypeEnum.OfflineUserDataJobType[
    offline_user_data_job.type_]
  status_name = offline_user_data_job_status.OfflineUserDataJobStatusEnum.OfflineUserDataJobStatus[
    offline_user_data_job.status]

  print(f'Offline user data job ID \'{offline_user_data_job.id}\' with type '
        f'\'{job_type}\' has status: {status_name}')

  if status_name == 'SUCCESS':
    print_customer_match_user_list_info(client, customer_id,
                                        user_list_resource_name)
  elif status_name == 'FAILED':
    print(f'\tFailure Reason: {offline_user_data_job.failure_reason}')
  elif status_name in ('PENDING', 'RUNNING'):
    print('To check the status of the job periodically, use the following '
          f'GAQL query with GoogleAdsService.Search: {query}')
    print('Or you can use the check_job.py script with the following args:')
    print(f'\npython check_job.py --config_file {args.config_file} '
          f'--customer_id {customer_id} '
          f'--job_resource_name {offline_user_data_job_resource_name} '
          f'--user_list_resource_name {user_list_resource_name} ')


def print_customer_match_user_list_info(client, customer_id,
                                        user_list_resource_name):
  """Prints information about the Customer Match user list.

  Args:
      client: The Google Ads client.
      customer_id: The customer ID for which to add the user list.
      user_list_resource_name: The resource name of the user list to which to
          add users.
  """
  googleads_service_client = client.get_service('GoogleAdsService')

  # Creates a query that retrieves the user list.
  query = f'''
      SELECT
        user_list.size_for_display,
        user_list.size_for_search
      FROM user_list
      WHERE user_list.resource_name = '{user_list_resource_name}'
  '''

  # Issues a search request.
  search_results = googleads_service_client.search(
      customer_id=customer_id, query=query)

  # Prints out some information about the user list.
  user_list = next(iter(search_results)).user_list
  print('The estimated number of users that the user list '
        f'\'{user_list.resource_name}\' has is '
        f'{user_list.size_for_display} for Display and '
        f'{user_list.size_for_search} for Search.')
  print('Reminder: It may take several hours for the user list to be '
        'populated. Estimates of size zero are possible.')


def upload_data(client,
                customer_id,
                list_name,
                list_type,
                customer_data,
                skip_polling,
                app_id=None):
  """Uploads processed data to the specified list and creates it if necessary.

  Args:
    client: The Google Ads client.
    customer_id: The customer ID for which to add the user list.
    list_name: The name of the user list to modify.
    list_type: The type of customer list (based on CustomerMatchUploadKeyType).
    customer_data: Processed customer data to be uploaded.
    skip_polling: A bool dictating whether to poll the API for completion.
    app_id: App ID required only for mobile advertising lists.

  Returns:
    None.
  """

  user_list_resource_name = get_user_list_resource_name(client, customer_id,
                                                        list_name)

  if not user_list_resource_name:
    # Create missing user list
    user_list_resource_name = create_user_list(client, customer_id, list_name,
                                               list_type, app_id)

  print(f'Uploading data for list \'{list_name}\'')
  add_users_to_customer_match_user_list(client, customer_id,
                                        user_list_resource_name, customer_data,
                                        skip_polling)


def normalize_and_sha256(s):
  """Normalizes (lowercase, remove whitespace) and hashes a string with SHA-256.

  Args:
    s: The string to perform this operation on.

  Returns:
    A normalized and SHA-256 hashed string.
  """
  return hashlib.sha256(s.strip().lower().encode()).hexdigest()


if __name__ == '__main__':
  parser = argparse.ArgumentParser(
      description='Uploads customer match list to Google Ads.')
  parser.add_argument(
      '--config_file',
      default=CONFIG_PATH,
      help='Configuration file for Google Ads API access.')
  parser.add_argument(
      '--customer_id',
      required=True,
      help='The customer ID for which to add the user list.')
  parser.add_argument(
      '--audience_file',
      default=CSV_FILE_PATH,
      help='CSV file with audience list.')
  parser.add_argument(
      '--list_type',
      default=CONTACT_INFO,
      choices=[CONTACT_INFO, MOBILE_ADVERTISING_ID, CRM_ID],
      help='Customer match upload key types. Default value: CONTACT_INFO')
  parser.add_argument(
      '--app_id',
      required=False,
      default=None,
      help=('App ID to associate with the list. Only required for '
            'Mobile Advertising Lists.'))
  parser.add_argument(
      '--hash_required',
      action='store_true',
      default=False,
      help='Indicates that the customer data needs to be hashed.')
  parser.add_argument(
      '--wait',
      action='store_true',
      default=False,
      help='Wait for the jobs to finish (each job will be blocking).')
  args = parser.parse_args()

  data = read_csv(args.audience_file, args.list_type, args.hash_required)

  google_ads_client = GoogleAdsClient.load_from_storage(args.config_file)

  for name in data:
    print(f'Processing data for list \'{name}\'.')
    try:
      if not is_list_empty(data[name]):
        upload_data(google_ads_client, args.customer_id, name, args.list_type,
                    data[name], not args.wait, args.app_id)
      else:
        print(f'The list \'{name}\' will be skipped as no compatible data '
              'has been found.')
    except GoogleAdsException as ex:
      print(f'Request with ID "{ex.request_id}" failed with status '
            f'"{ex.error.code().name}" and includes the following errors:')
      for single_error in ex.failure.errors:
        print(f'\tError with message "{single_error.message}".')
        if single_error.location:
          for field_path_element in single_error.location.field_path_elements:
            print(f'\t\tOn field: {field_path_element.field_name}')

  print('The process has finished.')
