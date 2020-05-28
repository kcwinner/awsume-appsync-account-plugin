import requests
import argparse
import json
import os
import sys
import boto3

from awsume.awsumepy import hookimpl, safe_print
from awsume.awsumepy.lib.logger import logger
from awsume.awsumepy.lib import exceptions

from requests_aws_sign import AWSV4Sign

ERROR_COLOR = '\033[91m'
WARNING_COLOR = '\033[93m'

CACHE_PATH = os.path.expanduser('~') + '/.appsync-plugin/'
CACHE_FILE = os.path.join(CACHE_PATH, 'accounts.json')

session = boto3.session.Session()
credentials = session.get_credentials()
region = session.region_name or 'us-east-2'

ROLE_PREFIX = 'appsync'
VALID_ROLES = [
    'readonly',
    'poweruser',
    'admin',
]

@hookimpl
def add_arguments(parser: argparse.ArgumentParser):
    try:
        parser.add_argument('--refresh-appsync',
            action='store_true',
            default=False,
            dest='refresh_appsync',
            help='Update the plugin\'s AppSync cache',
        )
    except argparse.ArgumentError:
        pass

@hookimpl
def post_add_arguments(config: dict, arguments: argparse.Namespace, parser: argparse.ArgumentParser):
    if arguments.refresh_appsync:
        print("Refreshing the AppSync cache", file=sys.stderr)
        __refresh_cache(config)
        if arguments.profile_name is None:
            exit(0)

@hookimpl
def pre_collect_aws_profiles(config: dict, arguments: argparse.Namespace, credentials_file: str, config_file: str):
    plugin_config = config.get('accounts_plugin', None)
    if plugin_config is not None:
        roles = plugin_config.get('roles', None)
        if roles is not None:
            global VALID_ROLES
            VALID_ROLES = roles

        role_prefix = plugin_config.get('role_prefix', None)
        if role_prefix is not None:
            global ROLE_PREFIX
            ROLE_PREFIX = role_prefix

    if not os.path.isdir(CACHE_PATH):
        os.makedirs(CACHE_PATH)

@hookimpl
def collect_aws_profiles(config: dict, arguments: argparse.Namespace, credentials_file: str, config_file: str):
    """The collect_aws_profiles plugin function."""
    role = __get_role(arguments.target_profile_name)
    region = arguments.region if arguments.region else 'us-east-2'
    source_profile = arguments.source_profile if arguments.source_profile else 'default'

    # If running 'awsume -l', no profile_name is given, but we don't want roles displayed
    profile_name_end = '-' + role if arguments.profile_name else ''

    appsync_accounts = __get_accounts(config)
    profiles = {}

    if appsync_accounts is None:
        safe_print('No profiles found from appsync', color=WARNING_COLOR)
        return profiles

    for account in appsync_accounts:
        profile_name = appsync_accounts[account]['name'] + profile_name_end
        profiles[profile_name] = __construct_config_profile(appsync_accounts[account], role, source_profile, region)
        if region:
            profiles[profile_name]['region'] = region

    return profiles

### AppSync Functions ###

def __get_accounts(config: dict):
    if os.path.isfile(CACHE_FILE):
        account_list = json.load(open(CACHE_FILE, 'r'))
    else:
        plugin_config = config.get('accounts_plugin', None)
        if plugin_config is None:
            safe_print('Accounts Plugin Not Configured. Cheack the README for instructions.', color=WARNING_COLOR)
            return {}
        account_list = __get_accounts_from_appsync(plugin_config)
    return __account_list_to_dict(account_list)

def __get_accounts_from_appsync(plugin_config: dict):
    """Make the call to get the aws accounts."""
    endpoint = plugin_config.get('appsync_url', None)
    if endpoint is None or endpoint == '':
        safe_print('AppSync URL Not Configured. Cheack the README for instructions.')
        return {}

    query = 'query {listAccounts {items {id name}}}'
    headers={"Content-Type": "application/json"}
    payload = {"query": query}
    service = 'appsync'
    appsync_region = __parse_region_from_url(endpoint) or region
    auth=AWSV4Sign(credentials, appsync_region, service)
    try:
        appsync_accounts = requests.post(
            endpoint,
            auth=auth,
            json=payload,
            headers=headers
        ).json()
        if 'errors' in appsync_accounts:
            safe_print('Error attempting to query AppSync', color=ERROR_COLOR)
            err = appsync_accounts['errors'][0]
            if 'errorType' in err and 'message' in err:
                errorType = err['errorType']
                errorMessage = err['message']
                safe_print(f'\t{errorType}: {errorMessage}', color=ERROR_COLOR)
            return {}
        else:
            appsync_accounts = appsync_accounts['data']['listAccounts']['items']
            if appsync_accounts is not None:
                __write_cache(appsync_accounts)
    except Exception as exception:
        appsync_accounts = {}
        safe_print("Cannot make the request to AppSync: ")
        safe_print(str(exception))
        safe_print("Make sure you are authorized to make the request")

    return appsync_accounts


### Role Functions ###

def __get_role(profile_name):
    """Get the role type of the target profile."""
    global VALID_ROLES
    role = profile_name.split('-')[-1]
    if not __is_valid_role_type(role):
        role = VALID_ROLES[0]
    return role

def __is_valid_role_type(role_type):
    """Return if the given role_type is a valid role."""
    if role_type not in VALID_ROLES:
        return False
    return True

### End Role Functions

### Utility Functions ###

def __account_list_to_dict(account_list):
    """Convert a list of aws accounts to a dict of aws accounts"""
    account_dict = {}
    if account_list is None:
        return account_dict

    for account in account_list:
        alias = account['name']
        account_dict[alias] = account
        account_dict[alias]['__name__'] = alias
    return account_dict

def __construct_config_profile(account, role, source_profile, region):
    """Construct the profile given the account, role, and options"""
    if account:
        role_arn = f'arn:aws:iam::{account["id"]}:role/{ROLE_PREFIX}-{role}'
        return {
            '__name__': account['name'], 
            'role_arn': role_arn,
            'source_profile': source_profile,
            'region': region
        }
    else:
        return {}

def __write_cache(accounts):
    with open(CACHE_FILE, 'w') as out_file:
        json.dump(accounts, out_file, indent=2)

def __refresh_cache(config: dict):
    plugin_config = config.get('accounts_plugin', None)
    if plugin_config is not None:
        __get_accounts_from_appsync(config)
    else:
        safe_print('Accounts Plugin Not Configured. Cheack the README for instructions.', color=WARNING_COLOR)

def __parse_region_from_url(url):
    """Parses the region from the appsync url so we call the correct region regardless of the session or the argument"""
    # Example URL: https://xxxxxxx.appsync-api.us-east-2.amazonaws.com/graphql
    split = url.split('.')
    if 2 < len(split):
        return split[2]
    return None

### End Utility Functions ###