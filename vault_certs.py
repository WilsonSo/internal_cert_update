#!/usr/bin/env python

import os
import sys
import json
import logging
import requests

def generate_certificate(attributes, vault_env, role, ttl='2160h'):

    # Parse generate certificate URL with role
    vault_generate_cert_url = "http://127.0.0.1:8200/v1/pki_int/issue/{}".format(role)

    # Set vault headers and vault payload
    vault_token = os.environ['VAULT_TOKEN'] # os.environ('bamboo_VAULT_TOKEN')
    vault_headers = {'X-Vault-Token': vault_token}

    vault_payload = {
                'common_name': attributes['common_name'],
                'alt_names': attributes['alt_name'],
                'ttl': ttl
                }

    # Make POST call to issue a new cert from the role
    resp = requests.post(vault_generate_cert_url, json=vault_payload, headers=vault_headers)
    if not resp.ok:
        logging.error("Unable to generate certificates from {}. Exiting".format(role))
        sys.exit(1)
    else:
        logging.info("Certificates successfully generated")

        certs = json.loads(resp.text)

        certificate = certs["data"]["certificate"]
        private_key = certs["data"]["private_key"]
        ca_chain = certs["data"]["ca_chain"][0]

        # Return certs for later use to update variables in TFE
        return certificate, private_key, ca_chain
