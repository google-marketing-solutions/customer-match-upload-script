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
[here](https://developers.google.com/adwords/api/docs/guides/authentication#installed)
to obtain a *Client ID* and *Client secret* for an *Installed App*.

Once you have the *Client ID*, and *Client secret*, you must obtain a *Refresh
token*:
```
python generate_refresh_token.py --client_id YOUR_CLIENT_ID --client_secret
YOUR_CLIENT_SECRET
```
Where `YOUR_CLIENT_ID` and `YOUR_CLIENT_SECRET` must be substituted with the
values you obtained previously.

The script will generate a *Refresh token* and print it on screen. Make a copy
of it as we'll need it later.

Next, get a *Developer token* from Google Ads by following the instructions
[here](https://developers.google.com/adwords/api/docs/guides/accounts-overview#developer_token)

Once you have the *Client ID*, *Client secret*, *Refresh token* and *Developer
token*, you must add them to the script config file. In order to do so, edit the
file `googleads_config.yaml` and enter the appropriate values. You'll also need
the Google Ads *Customer ID*, which you can find in Google Ads UI.

### Input preparation

Your audience file should be named `audience.csv` and must be in CSV format. You
must specify the fields to upload in the header row. The available fields are:

-   Email
-   Phone
-   MobileId
-   UserId
-   FirstName
-   LastName
-   CountryCode
-   ZipCode
-   List

You can use plain text values and the script will hash them before uploading, or
you can hash them yourself (the desired behaviour is controlled with the
`IS_DATA_ENCRYPTED` variable in the script).

### Running the script

Once the configuration file is ready, and you have the audience file in
`audience.csv` you can execute the script to upload the data to Google Ads:

```
python create_and_populate_list.py
```

If your audience file doesn't contain a column for the audience name, you can
specify a default audience to which all entries will be added. Here,
`YOUR_AUDIENCE_NAME` will typically be the name of the audience you manually
created in Google Ads for the purposes of this script:

```
python create_and_populate_list.py --audience_name YOUR_AUDIENCE_NAME
```

If you don't specify any remarketing list, either in the audience file or by
passing the `audience_name` parameter, the script will create a new audience
list and will add all the users to that one.

The script has more optional parameters that allow working with custom
configuration and audience file paths. For more info on them, run:

```
python create_and_populate_list.py --help
```
