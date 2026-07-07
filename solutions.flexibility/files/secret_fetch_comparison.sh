#!/bin/bash
set -e

# =============================================================================
# THE HARD WAY (without Kestra)
# -----------------------------------------------------------------------------
# A script that needs a secret usually has to assume an IAM role first, then
# make a SECOND API call to fetch + decrypt the value — before it can even
# start doing real work. This has to be re-implemented in every script and
# every language that needs a secret, and copy-pasted into every pipeline
# that calls it.
#
#   ROLE_ARN="arn:aws:iam::123456789012:role/demo-secret-reader"
#   CREDS=$(aws sts assume-role \
#     --role-arn "$ROLE_ARN" \
#     --role-session-name "flexibility-demo" \
#     --duration-seconds 900)
#
#   export AWS_ACCESS_KEY_ID=$(echo "$CREDS"     | jq -r '.Credentials.AccessKeyId')
#   export AWS_SECRET_ACCESS_KEY=$(echo "$CREDS" | jq -r '.Credentials.SecretAccessKey')
#   export AWS_SESSION_TOKEN=$(echo "$CREDS"     | jq -r '.Credentials.SessionToken')
#
#   # Option A — SSM Parameter Store
#   DB_PASSWORD=$(aws ssm get-parameter \
#     --name "/prod/db/password" \
#     --with-decryption \
#     --query "Parameter.Value" \
#     --output text)
#
#   # Option B — Secrets Manager
#   DB_PASSWORD=$(aws secretsmanager get-secret-value \
#     --secret-id "prod/db/password" \
#     --query "SecretString" \
#     --output text)
#
# That's a trust policy, an IAM role, an assume-role call, temporary
# credential plumbing, and a second API call — before the secret is even
# usable. Every language, every script, every pipeline pays this cost again.
# =============================================================================


# =============================================================================
# THE KESTRA WAY
# -----------------------------------------------------------------------------
# Kestra resolves the secret at runtime and hands it to this script as a
# plain environment variable — no IAM role, no assume-role call, no second
# API call. The flow just declares:
#
#   env:
#     DB_PASSWORD: "{{ secret('DEV_DB_PASSWORD') }}"
#
# and this script only has to do this:
# =============================================================================
if [[ -z "${DB_PASSWORD}" ]]; then
  echo "DB_PASSWORD was not resolved — configure that secret in Kestra first." >&2
  exit 1
fi

echo "Connecting to the database using the resolved secret..."
echo "DB_PASSWORD (masked): ${DB_PASSWORD:0:2}****${DB_PASSWORD: -2}"
# Bonus: Kestra also auto-redacts secret() values from the execution logs UI —
# the masking above is just this script being a good citizen on top of that.
