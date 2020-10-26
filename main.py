#!/usr/bin/env python

import os
import logging
import logging.config

# custom modules
import vault_certs
import terraform_variables

# Create logging mechanism
logging.config.fileConfig('logging.conf')

# Set basic attributes
env = os.environ['ENVIRONMENT'] # set in bamboo
role = 'example-dot-com' # api_web

attributes = {
        "uat": {
            "vault_server": "vault-nonprod-east",
            "common_name": "uat.east.internal.api.example.com",
            "alt_name": "uat.west.internal.api.example.com",
            "ttl": "24h",
            "workspace_name": "terraform-cloud-tier3",
            },
        "prod": {
            "vault_server": "vault-prod-east",
            "common_name": "prod.east.internal.api.example.com",
            "alt_name": "prod.west.internal.api.example.com",
            "ttl": "24h",
            "workspace_name": "terraform-cloud-tier2",
            }
        }

# Generate the internal certificate
certificate, private_key, ca_chain = vault_certs.generate_certificate(
    attributes = attributes[env],
    vault_env = "vault-nonprod-east",
    role = role
)

# Generate tfe workspace headers
tfe_workspace_headers = terraform_variables.get_tfe_workspace_headers(token=os.environ['TFE_TOKEN'])

# Get workspace id of the environment
tfe_workspace_id = terraform_variables.get_workspace_id(
    workspace_headers=tfe_workspace_headers,
    workspace_name=attributes[env]['workspace_name'],
    org='WilsonSo'
    )

# Create list of tuples of key, value and sensitive boolean
tfe_variable_properties = [
    ("internal_certificate", certificate, False),
    ("private_key", private_key, True),
    ("ca_chain", ca_chain, False)
    ]

# Create and upload terraform payloads
payload_dict = {}

for properties in tfe_variable_properties:
    tfe_variable_name = properties[0]
    tfe_variable_value = properties[1]
    tfe_variable_sensitive = properties[2]

    payload_dict[tfe_variable_name] = terraform_variables.TerraformVariablesPayload(
        key = tfe_variable_name,
        value = tfe_variable_value,
        sensitive = tfe_variable_sensitive
        )
    
    terraform_variables.upload_certs(
        workspace_headers = tfe_workspace_headers,
        workspace_id = tfe_workspace_id,
        variable_name = tfe_variable_name,
        payload_object = payload_dict[tfe_variable_name]
    )

logging.info("Certificate ending in {} was successfully uploaded to TFE workspace vars".format(certificate[-50:-26]))

# Trigger new run after TFE variables have been updated
terraform_variables.create_tfe_workspace_run(
    workspace_headers = tfe_workspace_headers,
    workspace_name = attributes[env]['workspace_name'],
    workspace_id = tfe_workspace_id,
    org = 'WilsonSo'
)