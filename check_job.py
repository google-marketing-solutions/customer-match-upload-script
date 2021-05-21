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
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

CONFIG_PATH = './googleads_config.yaml'


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
  status_name = offline_user_data_job.status.name

  print(f'Offline user data job ID \'{offline_user_data_job.id}\' with type '
        f'\'{offline_user_data_job.type_.name}\' has status: {status_name}')

  if status_name == 'SUCCESS':
    print_customer_match_user_list_info(client, customer_id,
                                        user_list_resource_name)
  elif status_name == 'FAILED':
    print(f'\tFailure Reason: {offline_user_data_job.failure_reason}')
  elif status_name in ('PENDING', 'RUNNING'):
    print('The job is still runnning.')


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


if __name__ == '__main__':
  parser = argparse.ArgumentParser(
      description='Check status of customer match list jobs in Google Ads.')
  parser.add_argument(
      '--config_file',
      default=CONFIG_PATH,
      help='Configuration file for Google Ads API access.')
  parser.add_argument(
      '--customer_id',
      required=True,
      help='The customer ID for which to add the user list.')
  parser.add_argument(
      '--job_resource_name',
      required=True,
      help='Offline user data job resource name to check.')
  parser.add_argument(
      '--user_list_resource_name',
      required=True,
      help='User list resource name.')
  args = parser.parse_args()

  google_ads_client = GoogleAdsClient.load_from_storage(args.config_file)

  try:
    check_job_status(google_ads_client, args.customer_id,
                     args.job_resource_name, args.user_list_resource_name)
  except GoogleAdsException as ex:
    print(f'Request with ID "{ex.request_id}" failed with status '
          f'"{ex.error.code().name}" and includes the following errors:')
    for single_error in ex.failure.errors:
      print(f'\tError with message "{single_error.message}".')
      if single_error.location:
        for field_path_element in single_error.location.field_path_elements:
          print(f'\t\tOn field: {field_path_element.field_name}')
