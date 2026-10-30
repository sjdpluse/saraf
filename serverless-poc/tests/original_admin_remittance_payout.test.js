import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=path=>readFileSync(new URL('../../'+path,import.meta.url),'utf8');
const sql=read('supabase/sql/saraf_original_admin_commands_STAGED.sql');
const edge=read('supabase/functions/saraf-original-admin/index.ts');
const ui=read('webapp/src/pages/OriginalAdmin.jsx');
const bridge=read('webapp/src/lib/originalAdminBridge.js');

test('original remittance payout RPC preserves six-digit pickup code and strict state machine',()=>{
 assert.match(sql,/CREATE OR REPLACE FUNCTION public\.saraf_original_admin_remittance/);
 assert.match(sql,/v_old='transfer_submitted'.*p_action IN \('ready','hold','cancel'\)/);
 assert.match(sql,/v_old='on_hold'.*p_action IN \('ready','cancel'\)/);
 assert.match(sql,/v_old='payout_ready'.*p_action IN \('hold','pay'\)/);
 assert.match(sql,/r\.pickup_code IS DISTINCT FROM p_pickup_code/);
 assert.match(sql,/INVALID_PICKUP_CODE/);
 assert.match(sql,/crypto_confirmed_by=CASE WHEN p_action='ready'/);
 assert.match(sql,/paid_by=CASE WHEN p_action='pay'/);
 assert.match(sql,/INSERT INTO public\.remittance_status_history/);
 assert.match(sql,/INSERT INTO public\.audit_log/);
 assert.match(sql,/REVOKE ALL ON FUNCTION public\.saraf_original_admin_remittance/);
 assert.match(sql,/GRANT EXECUTE ON FUNCTION public\.saraf_original_admin_remittance/);
});
test('original admin remittance payout uses Telegram HMAC & allowlist, never exposes code in JSON',()=>{
 assert.match(edge,/verifyTelegramInitData/);
 assert.match(edge,/if\(!isOwner\(actor\.id\)\)/);
 assert.match(edge,/if\(isWrite\(action\)&&!WRITE\)/);
 assert.match(edge,/if\(action==='remittances\.pending'\)/);
 assert.match(edge,/if\(action==='remittances\.transition'\)/);
 assert.match(edge,/saraf_original_admin_remittance/);
 assert.match(edge,/const \{beneficiary_id_document_path:discard,\.\.\.safe\}=row/);
 assert.match(edge,/bucket\.createSignedUrl\(path,90\)/);
 assert.match(edge,/customer_notified:notified/);
 assert.match(edge,/pickup_code.*v_next='payout_ready'/s);
 const segment=edge.slice(edge.indexOf("if(action==='remittances.transition')"),
   edge.indexOf("if(action==='broadcast.create')"));
 assert.match(segment,/order_id:result\.order_id,order_code:result\.order_code/);
 assert.doesNotMatch(segment,/return answer\(origin,200,\{result:saved\.data/);
});
test('admin UI requires independent beneficiary ID check and manual six-digit pickup proof',()=>{
 assert.match(ui,/transitionRemittance\(order,'pay'\)/);
 assert.match(ui,/pickupCodes\[order\.id\]/);
 assert.match(ui,/\/\^\[0-9\]\{6\}\$\//);
 assert.match(ui,/کد شش‌رقمی را از گیرنده/);
 assert.match(ui,/order\.verification_status/);
 assert.match(ui,/beneficiary_id_url/);
 assert.match(ui,/referrerPolicy="no-referrer"/);
 assert.match(bridge,/'remittances\.pending','remittances\.transition'/);
});
