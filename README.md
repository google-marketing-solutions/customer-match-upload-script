DISCLAIMER: This is not an officially supported Google product.

# Customer Match upload script

## About

This tool uploads Customer Match lists to Google Ads via API.

## Usage

### Google Ads setup

Before running the script, you should create a remarketing list in Google Ads.
It is recommended to set the membership duration to the N+3, where N is the
number of days between script runs. This way, the list will be maintained with
only those users that are in the audience file. If a user is removed from the
file, it won't be added in the next script run and it will be eventually
deleted. Matching process may take time; the *+3* is a safeguard period to avoid
unwanted tempororay removals during this processing time.

### Set-up

First, you must obtain the appropriate credentials so that the script can
connect to Google Ads API and upload the data. Follow the instructions
[here](https://developers.google.com/google-ads/api/docs/oauth/cloud-project#create_a_client_id_and_client_secret)
to obtain a OAuth 2.0 Client IDs for an *Installed App*. Then, download the
client secrets json file to the working directory (this file contains a
*Client ID* and *Client secret*).

Once you have the file, you must obtain a *Refresh token* using this script:

```shell
python generate_refresh_token.py --client_secrets_path CLIENT_SECRETS_FILE
```

Where `CLIENT_SECRETS_FILE` must be substituted with the client secrets file
path you downloaded previously.

The script will generate a *Refresh token* and print it on screen. Make a copy
of it as we'll need it later.

Next, get a *Developer token* from Google Ads by following the instructions
[here](https://developers.google.com/adwords/api/docs/guides/accounts-overview#developer_token)

Once you have the *Client ID*, *Client secret*, *Refresh token* and *Developer
token*, you must add them to the script config file. In order to do so, edit the
file `googleads_config.yaml` and enter the appropriate values. You'll also need
the Google Ads *MCC Customer ID*, which you can find in Google Ads UI.

### Input preparation

Your audience file should be named `audience.csv` and must be in CSV format. You
must specify the fields to upload in the header row. The available fields are:

- Email
- Phone
- MobileId
- UserId
- FirstName
- LastName
- CountryCode
- ZipCode
- List

You can use plain text values and the script will hash them before uploading, or
you can hash them yourself (the desired behaviour is controlled with the
`IS_DATA_ENCRYPTED` variable in the script).

### Running the script

Once the configuration file is ready, and you have the audience file in
`audience.csv` you can execute the script to upload the data to Google Ads:

```shell
python create_and_populate_list.py --customer_id CUSTOMER_ID
```

Where `CUSTOMER_ID` represents the Customer ID of the account where the user
list will be created.

If your audience file doesn't contain a column for the audience name, you can
specify a default audience to which all entries will be added. Here,
`YOUR_AUDIENCE_NAME` will typically be the name of the audience you manually
created in Google Ads for the purposes of this script:

```shell
python create_and_populate_list.py --customer_id CUSTOMER_ID --audience_name YOUR_AUDIENCE_NAME
```

If you don't specify any remarketing list in the audience file, the script will
create a new audience list with a default name (controlled by the `GENERIC_LIST`
variable in the script) and will add all the users to that one.

The script has more optional parameters that allow working with custom
configuration and audience file paths. For more info on them, run:

```shell
python create_and_populate_list.py --help
```

### Checking the results

By default, the script launches the upload jobs, and returns. You can use the
`--wait` flag to wait for the job to finish, but as the upload jobs can take up
to 48 hours to finish, waiting is not recommended.

If you don't specify the wait flag, the script will print the job ids in the
standard output, and the command you can use to check the job status.

This is an output example:

```txt
Offline user data job ID '9999999' with type 'CUSTOMER_MATCH_USER_LIST' has status: RUNNING
To check the status of the job periodically, use the following GAQL query with GoogleAdsService.Search:
        SELECT
          offline_user_data_job.resource_name,
          offline_user_data_job.id,
          offline_user_data_job.status,
          offline_user_data_job.type,
          offline_user_data_job.failure_reason
        FROM offline_user_data_job
        WHERE offline_user_data_job.resource_name =
          'customers/0000000000/offlineUserDataJobs/9999999'
        LIMIT 1
Or you can use the check_job.py script with the following args:

 python check_job.py --config_file ./csemcc_config.yaml --customer_id 0000000000 --job_resource_name customers/0000000000/offlineUserDataJobs/9999999 --user_list_resource_name customers/0000000000/userLists/888888888
```
