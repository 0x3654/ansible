#!/usr/bin/env bash
# script-torrent-added hook: decide destination by file names right at add time.
# If a torrent lands in a */movie dir but its files look like episodes (SxxEyy),
# relocate it to the sibling */tv show dir and force a recheck, so an updated
# season pack reuses already downloaded files instead of starting from scratch.
# The final check after completion stays in transmission-postprocess.sh.
set -uo pipefail

log() {
  printf '[%s] added-hook: %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" >&2
}

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    log "Missing required command: $1"
    exit 1
  fi
}

require_command curl
require_command jq

: "${TR_TORRENT_ID:?Transmission did not pass TR_TORRENT_ID}"
: "${TR_TORRENT_NAME:?Transmission did not pass TR_TORRENT_NAME}"
: "${TR_TORRENT_DIR:?Transmission did not pass TR_TORRENT_DIR}"

RPC_HOST="${TRANSMISSION_RPC_HOST:-127.0.0.1}"
RPC_PORT="${TRANSMISSION_RPC_PORT:-9091}"
RPC_PATH="${TRANSMISSION_RPC_PATH:-/transmission/rpc}"
RPC_URL="${TRANSMISSION_RPC_URL:-http://${RPC_HOST}:${RPC_PORT}${RPC_PATH}}"
RPC_USERNAME="${TRANSMISSION_RPC_USERNAME:-}"
RPC_PASSWORD="${TRANSMISSION_RPC_PASSWORD:-}"
# how long to wait for file names (magnet links get them only after metadata)
METADATA_WAIT="${ADDED_HOOK_METADATA_TIMEOUT:-120}"

log "Torrent '${TR_TORRENT_NAME}' (ID: ${TR_TORRENT_ID}) added in '${TR_TORRENT_DIR}'"

if [[ "$TR_TORRENT_ID" =~ ^[0-9]+$ ]]; then
  TORRENT_IDS_JSON="[$TR_TORRENT_ID]"
else
  TORRENT_IDS_JSON=$(jq -cn --arg id "$TR_TORRENT_ID" '[ $id ]')
fi

SESSION_ID=""

call_rpc() {
  local method=$1
  local args=${2:-{}}
  local payload
  if [[ "$args" == "{}" ]]; then
    payload="{\"method\":\"${method}\"}"
  else
    payload="{\"method\":\"${method}\",\"arguments\":${args}}"
  fi

  while true; do
    local header body http_code
    header=$(mktemp)
    body=$(mktemp)
    local curl_args=(-sS -D "$header" -o "$body" -H "Content-Type: application/json")
    if [[ -n "$SESSION_ID" ]]; then
      curl_args+=(-H "X-Transmission-Session-Id: $SESSION_ID")
    fi
    if [[ -n "$RPC_USERNAME" ]]; then
      curl_args+=(-u "${RPC_USERNAME}:${RPC_PASSWORD}")
    fi
    if ! curl "${curl_args[@]}" --data "$payload" "$RPC_URL"; then
      log "Failed to contact Transmission RPC at ${RPC_URL}"
      rm -f "$header" "$body"
      exit 1
    fi
    http_code=$(awk 'NR==1 {print $2}' "$header")
    if [[ "$http_code" == "409" ]]; then
      SESSION_ID=$(awk 'BEGIN{IGNORECASE=1} /^X-Transmission-Session-Id/ {print $2}' "$header" | tr -d '\r')
      rm -f "$header" "$body"
      continue
    fi
    if [[ "$http_code" != "200" ]]; then
      log "RPC call '${method}' failed with HTTP status ${http_code}"
      cat "$body" >&2
      rm -f "$header" "$body"
      exit 1
    fi
    cat "$body"
    rm -f "$header" "$body"
    break
  done
}

# RSS already targets tv show — nothing to decide
if [[ "${TR_TORRENT_DIR,,}" == *"/tv show"* ]]; then
  log "Already targets tv show dir; nothing to decide"
  exit 0
fi

# Only decide for the default movie destination; other dirs stay untouched
if [[ "$TR_TORRENT_DIR" != *"/movie"* ]]; then
  log "Not a /movie dir; nothing to decide"
  exit 0
fi

args_files=$(jq -cn --argjson ids "$TORRENT_IDS_JSON" '{ids:$ids,"fields":["files"]}')

data=""
deadline=$(( $(date +%s) + METADATA_WAIT ))
while :; do
  data=$(call_rpc "torrent-get" "$args_files")
  if [[ -n "$(jq -r '.arguments.torrents[0].files[]?.name' <<<"$data" | head -n1)" ]]; then
    break
  fi
  if (( $(date +%s) >= deadline )); then
    log "No file names after ${METADATA_WAIT}s (magnet without metadata?); falling back to torrent name"
    data=""
    break
  fi
  sleep 2
done

is_series=0
if [[ -n "$data" ]]; then
  while IFS= read -r relpath; do
    [[ -z "$relpath" ]] && continue
    if [[ "$relpath" =~ [sS][0-9]{2}[[:space:]._-]*[eE][0-9]{2} ]]; then
      is_series=1
      break
    fi
  done < <(jq -r '.arguments.torrents[0].files[]?.name' <<<"$data")
elif [[ "$TR_TORRENT_NAME" =~ [sS][0-9]{2}[[:space:]._-]*[eE][0-9]{2} ]]; then
  is_series=1
fi

if (( is_series == 0 )); then
  log "No SxxEyy pattern in file names; leaving in movie (postprocess re-checks after download)"
  exit 0
fi

new_dir="${TR_TORRENT_DIR/\/movie/\/tv show}"
if [[ "$new_dir" == "$TR_TORRENT_DIR" ]]; then
  log "No path change computed; nothing to do"
  exit 0
fi

log "Episode files detected; relocating to '${new_dir}' and forcing recheck"
call_rpc "torrent-set-location" "$(jq -cn --argjson ids "$TORRENT_IDS_JSON" --arg loc "$new_dir" '{ids:$ids,"location":$loc,"move":true}')" >/dev/null
call_rpc "torrent-verify" "$(jq -cn --argjson ids "$TORRENT_IDS_JSON" '{ids:$ids}')" >/dev/null
call_rpc "torrent-start" "$(jq -cn --argjson ids "$TORRENT_IDS_JSON" '{ids:$ids}')" >/dev/null
log "Done: '${TR_TORRENT_NAME}' relocated to '${new_dir}', recheck queued"
