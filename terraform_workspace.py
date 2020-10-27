#!/usr/bin/env python

import os
import json
import logging
import requests

class TerraformVariablesPayload:
    """Payload used to upload to Terraform Vars

    Attributes:
        payload: payload generated to upload to Terraform workspace variables

    Methods:
        create_variable: Makes POST request to TFE if variable does not currently exist
        update_variable: Makes PATCH request to update TFE variable
    """

    def __init__(self, key, value, description="", sensitive=False):

        """Inits TerraformPayload with payload data needed for Terraform Vars"""

        self.key = key
        self.value = value
        self.description = description
        self.sensitive = sensitive

        self.payload = {
            "data": {
                "type": "vars",
                "attributes": {
                    "key": self.key,
                    "value": self.value,
                    "description": self.description,
                    "category":"terraform",
                    "hcl": False,
                    "sensitive": self.sensitive
                }
            }
        }

    def create_variable(self, url, headers):

        """Makes POST request to workspace variable API to create variable """

        res = requests.post(url, json=self.payload, headers=headers)
        if not res.ok:
            logging.error("An error occurred creating the variable {}".format(self.key))
            raise SystemExit(1)
        else:
            logging.info("Terraform var {} was successfully created".format(self.key))

    def update_variable(self, url, headers, var_id):

        """Makes PATCH request to workspace variable API to update variable """

        # append variable ID to payload in order to make PATCH call
        self.payload['data']['id'] = var_id
        res = requests.patch(url, json=self.payload, headers=headers)
        if not res.ok:
            logging.error("An error occurred updating the variable {}".format(self.key))
            raise SystemExit(1)
        else:
            logging.info("Terraform var {} was successfully updated".format(self.key))

    

def get_tfe_workspace_headers(token):
    
    # Create headers for get request
    terraform_token = os.environ['TFE_TOKEN']
    bearer_token = "Bearer {}".format(terraform_token)

    tfe_workspace_headers = {
        "Authorization": bearer_token,
        "Content-Type": "application/vnd.api+json"
    }

    return tfe_workspace_headers

def get_workspace_id(workspace_headers, workspace_name, org='CCBD'):

    # determine workspace id of environment
    workspace_list_url = 'https://app.terraform.io/api/v2/organizations/{}/workspaces'.format(org) # CCBD

    res = requests.get(workspace_list_url, headers=workspace_headers)
    if not res.ok:
        logging.error("Unable to retrieve list of workspaces from TFE")
        raise SystemExit(1)
    else:
        workspaces = json.loads(res.text)

        # return json object data of workspace we're searching for
        workspace = list(filter(lambda x:x["attributes"]["name"]==workspace_name, workspaces['data']))[0] 
        return workspace['id']

def upload_certs_to_tfe(workspace_headers, workspace_id, variable_name, payload_object):
    
    # Set workspace vars api to upload to
    workspace_vars_url = "https://app.terraform.io/api/v2/workspaces/{}/vars".format(workspace_id)

    # Determine if variable already exists. If it does, we make a PATCH call instead of POST
    res = requests.get(workspace_vars_url, headers=workspace_headers)
    if not res.ok:
        logging.error("Unable to retrieve list of variables for workspace {}".format(workspace_id))
        raise SystemExit(1)
    else:
        workspace_vars = json.loads(res.text)['data']
        try:
            variables = list(filter(lambda x:x["attributes"]["key"]==variable_name,workspace_vars))[0]
            var_id = variables['id']
            logging.info("Existing variable found for {}, updating terraform variable".format(variable_name))
            workspace_vars_url = "https://app.terraform.io/api/v2/workspaces/{}/vars/{}".format(workspace_id,var_id)
            payload_object.update_variable(url=workspace_vars_url, headers=workspace_headers, var_id=var_id)
        except:
            logging.info("No variables found matching {}. Creating now".format(variable_name))
            workspace_vars_url = "https://app.terraform.io/api/v2/workspaces/{}/vars".format(workspace_id)
            payload_object.create_variable(url=workspace_vars_url, headers=workspace_headers)

def trigger_tfe_workspace_run(workspace_headers, workspace_name, workspace_id, target_resources="", org='CCBD'):

    # POST call to run api to trigger new run
    # Set URL for runs
    tfe_run_url = "https://app.terraform.io/api/v2/runs"

    # Create run payload
    payload = {
        'data': {
            'attributes': {
                'message': 'Run triggered after updating certs',
                'target-addrs': target_resources
            },
            'type': 'runs',
            'relationships': {
                'workspace': {
                    'data': {
                        'type': 'workspaces',
                        'id': workspace_id
                    }
                }
            }
        }
    }
    
    res = requests.post(tfe_run_url, json=payload, headers=workspace_headers)
    if not res.ok:
        logging.error("An error occurred triggering run in workspace {}".format(workspace_id))
        raise SystemExit(1)
    else:
        run_res = json.loads(res.text)['data']
        run_id = run_res['id']
        run_url = "https://app.terraform.io/app/{}/workspaces/{}/runs/{}".format(
            org, workspace_name, run_id
        )
        logging.info("The run was successfully triggered and can be found at {}".format(run_url))