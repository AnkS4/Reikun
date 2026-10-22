#!/usr/bin/env bash
# Retry-launch an Always Free Ampere A1 VM on OCI until capacity appears.
# Pair with oci-a1-retry.service (systemd user unit, no tmux).
set -uo pipefail

# Exit codes: 0 done, 1 transient (systemd restarts), 2 fatal (no restart).
readonly E_OK=0
readonly E_TRANSIENT=1
readonly E_FATAL=2

# ---------- EDIT THESE ----------
COMPARTMENT_ID="ocid1.tenancy.oc1..aaaaaaaakxcgojzzvk4wwlbhgdi4nhdziqe4hvgj2mdkiascksg67cvwlkfa"      # root compartment = tenancy OCID
SUBNET_ID="ocid1.subnet.oc1.eu-madrid-3.aaaaaaaafo2hsqsyktcvgkksb4j3frda2g55wu5d2wdka4faxhpi4cs75qpq"            # your PUBLIC subnet
SSH_PUB_KEY_FILE="$HOME/.ssh/oci_a1.pub"          # public key file (see notes)
DISPLAY_NAME="reikun-vm"
OCPUS=2                                      # Always Free total: 4 OCPU / 24 GB
MEMORY_GB=12
BOOT_VOLUME_GB=50                            # free tier total block storage: 200 GB
RETRY_SECONDS=120                            # base wait; random jitter added
MAX_UNKNOWN_ERRORS=5                         # consecutive unrecognised errors before giving up
IMAGE_OS_VERSION="26.04"
IMAGE_ID=""                                  # set to pin an image OCID
# --------------------------------

SHAPE="VM.Standard.A1.Flex"
LOCK_FILE="${XDG_CACHE_HOME:-$HOME/.cache}/oci-a1-retry.lock"

die() { echo "FATAL: $*" >&2; exit "$E_FATAL"; }
transient() { echo "TRANSIENT: $*" >&2; exit "$E_TRANSIENT"; }

command -v oci >/dev/null || die "oci CLI not found in PATH ($PATH)"
[[ $COMPARTMENT_ID == ocid1.* && $COMPARTMENT_ID != *xxx* ]] || die "COMPARTMENT_ID unset or placeholder"
[[ $SUBNET_ID == ocid1.* && $SUBNET_ID != *xxx* ]] || die "SUBNET_ID unset or placeholder"
[[ $SSH_PUB_KEY_FILE != *xxx && -r $SSH_PUB_KEY_FILE ]] || die "SSH_PUB_KEY_FILE missing/unreadable: $SSH_PUB_KEY_FILE"

if [[ -f $HOME/.oci/config ]] && grep -Eq '^[[:space:]]*security_token_file[[:space:]]*=' "$HOME/.oci/config"; then
  die "OCI config uses session-token auth; switch to an API key for a long-running retry"
fi

mkdir -p "$(dirname "$LOCK_FILE")"
exec 9>"$LOCK_FILE"
flock -n 9 || { echo "already running (lock $LOCK_FILE); exiting"; exit "$E_OK"; }

# NOTE: JMESPath queries stay in single quotes; inside double quotes bash would
# run `...` as command substitution and break the query.
existing_instance_ids() {
  oci compute instance list \
    --compartment-id "$COMPARTMENT_ID" \
    --display-name "$DISPLAY_NAME" \
    --query 'data[?contains(`["PROVISIONING","RUNNING","STARTING","STOPPING","STOPPED","CREATING_IMAGE"]`, "lifecycle-state")].id | join(`"\n"`, @)' \
    --raw-output
}

if ! ids=$(existing_instance_ids); then
  transient "could not list instances (network/auth?)"
fi
if [[ -n $ids ]]; then
  echo "Instance already present for $DISPLAY_NAME:"; echo "$ids"
  exit "$E_OK"
fi

if [[ -z $IMAGE_ID ]]; then
  # No --operating-system-version: that filter is an exact match, and Minimal
  # images report a version like "26.04 Minimal", so "26.04" never matches them.
  # We match on the display name instead. --all avoids missing a second page.
  IMAGE_ID=$(oci compute image list \
    --compartment-id "$COMPARTMENT_ID" \
    --operating-system "Canonical Ubuntu" \
    --shape "$SHAPE" \
    --all \
    --sort-by TIMECREATED --sort-order DESC \
    --query 'data[?contains("display-name", `"'"$IMAGE_OS_VERSION"'"`) && contains("display-name", `"Minimal"`) && contains("display-name", `"aarch64"`)] | [0].id' \
    --raw-output 2>/dev/null) || IMAGE_ID=""
fi
if [[ $IMAGE_ID != ocid1.image.* ]]; then
  echo "Images visible for $SHAPE (pin one via IMAGE_ID):" >&2
  oci compute image list --compartment-id "$COMPARTMENT_ID" --operating-system "Canonical Ubuntu" \
    --shape "$SHAPE" --all --query 'data[].{name:"display-name",ver:"operating-system-version",id:id}' --output table >&2 || true
  die "no image matched '$IMAGE_OS_VERSION' + Minimal + aarch64"
fi
IMAGE_NAME=$(oci compute image get --image-id "$IMAGE_ID" \
  --query 'data."display-name"' --raw-output) || transient "could not read image name"
echo "Image: $IMAGE_ID ($IMAGE_NAME)"

ad_out=$(oci iam availability-domain list \
  --compartment-id "$COMPARTMENT_ID" \
  --query 'data[].name | join(`"\n"`, @)' --raw-output) \
  || transient "could not list availability domains"
ADS=()
while IFS= read -r line; do
  line=${line//$'\r'/}
  [[ -n $line ]] && ADS+=("$line")
done <<<"$ad_out"
[[ ${#ADS[@]} -gt 0 ]] || die "no availability domains returned"
echo "Availability domains: ${ADS[*]}"

RETRYABLE='out of host capacity|out of capacity|TooManyRequests|"status": (429|500|502|503|504)|InternalError|Max wait time has been exceeded|ConnectionError|Max retries exceeded|Failed to establish|Name or service not known|Temporary failure in name resolution|timed out|RequestException|EndpointConnectionError'

attempt=0
unknown=0
while true; do
  if ! ids=$(existing_instance_ids); then
    echo "  warning: instance list failed; will try launch anyway"
  elif [[ -n $ids ]]; then
    echo "SUCCESS: instance already present:"; echo "$ids"
    exit "$E_OK"
  fi

  for AD in "${ADS[@]}"; do
    attempt=$((attempt + 1))
    echo "[$(date '+%F %T')] attempt $attempt in $AD"
    out=$(oci compute instance launch \
      --compartment-id "$COMPARTMENT_ID" \
      --availability-domain "$AD" \
      --shape "$SHAPE" \
      --shape-config "{\"ocpus\": $OCPUS, \"memoryInGBs\": $MEMORY_GB}" \
      --subnet-id "$SUBNET_ID" \
      --assign-public-ip true \
      --image-id "$IMAGE_ID" \
      --boot-volume-size-in-gbs "$BOOT_VOLUME_GB" \
      --ssh-authorized-keys-file "$SSH_PUB_KEY_FILE" \
      --display-name "$DISPLAY_NAME" \
      --wait-for-state RUNNING \
      --max-wait-seconds 900 2>&1) && rc=0 || rc=$?

    if [[ $rc -eq 0 ]]; then
      echo "SUCCESS:"; echo "$out"
      exit "$E_OK"
    fi

    if grep -qiE "$RETRYABLE" <<<"$out"; then
      unknown=0
      echo "  no capacity / throttled / network / transient, will retry"
    elif grep -qE 'NotAuthenticated|NotAuthorizedOrNotFound|LimitExceeded|InvalidParameter|"status": 40[0134]' <<<"$out"; then
      echo "Non-retryable error, stopping:"; echo "$out"
      exit "$E_FATAL"
    else
      unknown=$((unknown + 1))
      echo "  unrecognised error ($unknown/$MAX_UNKNOWN_ERRORS):"; echo "$out" | head -n 15
      (( unknown >= MAX_UNKNOWN_ERRORS )) && die "too many unrecognised errors in a row"
    fi
  done
  sleep $((RETRY_SECONDS + RANDOM % 60))
done
