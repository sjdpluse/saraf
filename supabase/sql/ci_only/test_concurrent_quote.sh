#!/usr/bin/env bash
# GitHub Actions EPHEMERAL PostgreSQL only. Never connect to production.
set -euo pipefail
quote_id=$(psql -X -q -tA -v ON_ERROR_STOP=1 \
  -c "select (public.saraf_issue_quote_atomic(101,'USDT','buy',80.00)->>'quote_id');" | tr -d '[:space:]')
[[ "$quote_id" =~ ^[0-9]+$ ]] || { echo "Cannot create test quote"; exit 1; }
details='{"asset":"USDT","action":"buy","network":"ERC20","payment_method":"in_person","exchange_name":"Race Test Provider","wallet_address":"0x1111111111111111111111111111111111111111"}'
set +e
psql -X -v ON_ERROR_STOP=1 -c "select public.saraf_submit_order_atomic(101,$quote_id,'race-quote-token-aaaaaaa','$details'::jsonb);" >/tmp/saraf-race-a.log 2>&1 &
a=$!
psql -X -v ON_ERROR_STOP=1 -c "select public.saraf_submit_order_atomic(101,$quote_id,'race-quote-token-bbbbbbb','$details'::jsonb);" >/tmp/saraf-race-b.log 2>&1 &
b=$!
wait "$a"; code_a=$?
wait "$b"; code_b=$?
set -e
if [[ "$code_a" == "$code_b" ]]; then
  echo "::error::Expected exactly one successful concurrent consumer of a quote."
  exit 1
fi
number=$(psql -X -q -tA -v ON_ERROR_STOP=1 \
  -c "select count(*) from public.usdt_orders where quote_id=$quote_id;" | tr -d '[:space:]')
[[ "$number" == "1" ]] || { echo "::error::Expected exactly one order, found $number"; exit 1; }
state=$(psql -X -q -tA -v ON_ERROR_STOP=1 \
  -c "select status from public.usdt_quotes where id=$quote_id;" | tr -d '[:space:]')
[[ "$state" == "consumed" ]] || { echo "::error::Quote not consumed"; exit 1; }
echo "PASS: one atomic consumer wins and the other loses; no duplicate financial order."
