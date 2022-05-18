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
"""This example creates an OAuth 2.0 refresh token for the Google Ads API.

This illustrates how to step through the OAuth 2.0 native / installed
application flow.

It is intended to be run from the command line and requires user input.
"""

import argparse
import json
import re

from google_auth_oauthlib.flow import Flow

SCOPE = 'https://www.googleapis.com/auth/adwords'


def main(client_secrets_path, scopes):
  with open(client_secrets_path) as client_secrets_file:
      client_secrets = json.load(client_secrets_file)
      redirect_uri = client_secrets['installed']['redirect_uris'][0]
  flow = Flow.from_client_secrets_file(
      client_secrets_path, scopes=scopes, redirect_uri=redirect_uri)
  print('Please open this URL in your browser and follow the prompts to '
        'authorize this script: '
        f'{flow.authorization_url()[0]}')
  print(f"""
If there is no local web server serving at {redirect_uri}, the \
succeeded OAuth flow will land the browser on an error page ("This site \
can't be reached"). This is an expected behavior. Copy the whole URL and \
continue.
  """)
  url = input('Copy the code (or the complete url if no code is shown) '
              'from the browser and paste it here: ')
  code = re.sub(r'&.*$','', re.sub(r'^.*code=', '', url))

  flow.fetch_token(code=code)

  print('Access token: %s' % flow.credentials.token)
  print('Refresh token: %s' % flow.credentials.refresh_token)


if __name__ == '__main__':
  parser = argparse.ArgumentParser(
      description='Generates OAuth 2.0 credentials with the specified '
      'client secrets file.')
  # The following argument(s) should be provided to run the example.
  parser.add_argument(
      '--client_secrets_path',
      required=True,
      help=('Path to the client secrets JSON file from the '
            'Google Developers Console that contains your '
            'client ID and client secret.'),
  )
  parser.add_argument(
      '--additional_scopes',
      default=None,
      help=('Additional scopes to apply when generating the '
            'refresh token. Each scope should be separated '
            'by a comma.'),
  )
  args = parser.parse_args()

  configured_scopes = [SCOPE]

  if args.additional_scopes:
    configured_scopes.extend(args.additional_scopes.replace(' ', '').split(','))

  main(args.client_secrets_path, configured_scopes)

