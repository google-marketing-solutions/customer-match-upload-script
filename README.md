DISCLAIMER: This is not an officially supported Google product.

# Customer upload tool

## About

This tool uploads Customer Match lists to Google Ads via API.

## Usage

### Set-up

First, you must obtain the appropriate credentials so that the script
can connect to Google Ads API and upload the data. Follow the instructions 
[here](https://developers.google.com/adwords/api/docs/guides/authentication#installed)
to obtain a *Client ID* and *Client secret* for an *Installed App*.

Once you have the *Client ID*, and *Client secret*, you must obtain a *Refresh
token*:
```
python generate_refresh_token.py --client_id YOUR_CLIENT_ID --client_secret
YOUR_CLIENT_SECRET
```
Where `YOUR_CLIENT_ID` and `YOUR_CLIENT_SECRET` must be substituted
with the values you obtained previously.

The script will generate a *Refresh token* and print it on screen. Make a copy
of it as we'll need it later.

Next, get a *Developer token* from Google Ads by following the instructions
[here](https://developers.google.com/adwords/api/docs/guides/accounts-overview#developer_token)

Once you have the *Client ID*, *Client secret*, *Refresh token* and *Developer
token*, you must add them to the script config file. In order to do so, edit the
file `googleads_config.yaml` and enter the appropriate values. You'll also need
the Google Ads *Customer ID*, which you can find in Google Ads UI.

### Running the script

Once the configuration file is ready, and you have the audience file in
`audience.csv` you can execute the script to upload the data to Google Ads:

```
python create_and_populate_list.py
```

If your audience file doesn't contain a column for the audience name, you can
specify a default audience to which all entries will be added:

```
python create_and_populate_list.py --audience_name YOUR_AUDIENCE_NAME
```

The script has more optional parameters that allow working with custom
configuration and audience file paths. For more info on them, run:

```
python create_and_populate_list.py --help
```
