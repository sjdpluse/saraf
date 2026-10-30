import test from 'node:test';
import assert from 'node:assert/strict';
import { createHmac } from 'node:crypto';
import { verifyTelegramInitData } from '../../supabase/functions/saraf-telegram-bridge/telegram-auth.mjs';

const TOKEN='123456:FAKE_TEST_ONLY_NEVER_REAL';
const NOW=1793257200;
const user=JSON.stringify({id:123456789,first_name:'Test User',username:'test_user'});
function signedInitData(entries,{token=TOKEN}={}) {
  const keys=Object.keys(entries).sort();
  const source=keys.map(key=>key+'='+entries[key]).join('\n');
  const secret=createHmac('sha256','WebAppData').update(token).digest();
  const hash=createHmac('sha256',secret).update(source).digest('hex');
  const params=new URLSearchParams({...entries,hash});
  return params.toString();
}
const valid=signedInitData({auth_date:String(NOW),user,query_id:'AAEtest_query'});
test('accepts authentic Telegram Mini App HMAC and reads ONLY signed user ID',async()=>{
  const output=await verifyTelegramInitData(valid,TOKEN,NOW);
  assert.equal(output?.id,123456789);
  assert.equal(output?.username,'test_user');
});
test('refuses tampered account ID and wrong bot token',async()=>{
  const forged=valid.replace('123456789','999999999');
  assert.equal(await verifyTelegramInitData(forged,TOKEN,NOW),null);
  assert.equal(await verifyTelegramInitData(valid,'999999:OTHER_BOT_TOKEN',NOW),null);
});
test('refuses expired signed requests and future forged timestamp',async()=>{
  assert.equal(await verifyTelegramInitData(valid,TOKEN,NOW+3601),null);
  assert.equal(await verifyTelegramInitData(valid,TOKEN,NOW-61),null);
});
test('refuses duplicate hash or duplicate signed fields',async()=>{
  assert.equal(await verifyTelegramInitData(valid+'&hash='+('f'.repeat(64)),TOKEN,NOW),null);
  assert.equal(await verifyTelegramInitData(valid+'&user='+encodeURIComponent(user),TOKEN,NOW),null);
});
test('refuses omitted fields, invalid bot token, and a replay with malformed identity',async()=>{
  assert.equal(await verifyTelegramInitData('fake','',NOW),null);
  assert.equal(await verifyTelegramInitData(valid,'TOKENWITHOUTBOTID',NOW),null);
  const wrong=signedInitData({auth_date:String(NOW),user:JSON.stringify({id:'not-an-integer'})});
  assert.equal(await verifyTelegramInitData(wrong,TOKEN,NOW),null);
});
