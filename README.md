# AWSume AppSync Account Plugin

## AWSume Configuration

This plugin requires the AWSume config to be setup correctly. Below are the three config items required for the plugin to work correctly:

* The most important value is the url of the AppSync API. This is mandatory and does not have a default value.
  * `awsume --config set 'accounts_plugin.appsync_url' 'https://xxxxxxx.appsync-api.us-east-2.amazonaws.com/graphql'`
* You can set the role names that your organization uses. Defaults to ['readonly', 'poweruser', 'admin'].
  * `awsume --config set 'accounts_plugin.roles' '["readonly", "billing", "poweruser", "admin"]'`
* You can also set the role prefex for your roles. Defaults to 'appsync'. 
  * `awsume --config set 'accounts_plugin.role_prefix' 'your-cool-company-name'`
  * Resulting roles are assumed to look something like `${prefix}-${account_name}-${role}` such as `aws-dev-admin`.

The resulting AWSume config will look as follows:

```yaml
accounts_plugin:
  appsync_url: https://xxxxxxx.appsync-api.us-east-2.amazonaws.com/graphql
  roles:
    - readonly
    - billing
    - poweruser
    - admin
  role_prefix: your-cool-company-name
colors: true 
fuzzy-match: false
role-duration: 0
```

## Future Improvements

* Region

## Limitations

* AppSync needs to be created in the IAM account due to using IAM access as authorization on the AppSync API. AppSync does not currently support cross-account IAM access. 
    * There are some ways around this but I don't believe the benefits outweigh the extra management. Such as IAM access to an API Gateway endpoint in another account
    * Dynamo tables can still be setup in another account if desired. Just manage the service role for the datasource to have access to the other account