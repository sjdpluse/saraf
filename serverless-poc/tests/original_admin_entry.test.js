import test from 'node:test';
import assert from 'node:assert/strict';
import {parseOriginalAdminCommand} from '../tgcloud/lib/original_admin_parse.js';

test('existing Saraf 6 admin command names and exact meaning preserved',()=>{
 const names=['stats','spreads','setspread','usdtpending','usdtconfirm','broadcast'];
 for(const name of names)assert.equal(parseOriginalAdminCommand('/'+name)?.name,name);
 assert.equal(parseOriginalAdminCommand('/stats@sarafiaf_bot')?.name,'stats');
 assert.equal(parseOriginalAdminCommand('/notadmin'),null);
});
test('valid original /setspread carries bounded code and percentage to signed app',()=>{
 const result=parseOriginalAdminCommand('/setspread usd 0.8');
 assert.equal(result.query.get('action'),'admin');
 assert.equal(result.query.get('admin'),'setspread');
 assert.equal(result.query.get('currency'),'usd');
 assert.equal(result.query.get('percent'),'0.8');
 for(const value of ['/setspread usd 25','/setspread secret 1',
  '/setspread usd Infinity','/setspread usd 0.8;delete']){
  const bad=parseOriginalAdminCommand(value);
  assert.ok(bad.usage);
  assert.equal(bad.query.get('currency'),null);
  assert.equal(bad.query.get('percent'),null);
 }
});
test('original order IDs are parsed without mutation or executing an order',()=>{
 const result=parseOriginalAdminCommand('/usdtconfirm USDT-12');
 assert.equal(result.query.get('order_id'),'12');
 assert.equal(result.query.get('admin'),'confirm');
 const invalid=parseOriginalAdminCommand('/usdtconfirm nonsense');
 assert.ok(invalid.usage);
 assert.equal(invalid.query.get('order_id'),null);
});
test('original /broadcast opens signed admin composer without directly transmitting',()=>{
 const item=parseOriginalAdminCommand('/broadcast hello all');
 assert.equal(item.name,'broadcast');
 assert.equal(item.query.get('action'),'admin');
 assert.equal(item.query.get('admin'),'broadcast');
 assert.equal(item.query.get('broadcast'),'hello all');
 assert.match(item.usage,/تایید هویت/);
 const tooLong=parseOriginalAdminCommand('/broadcast '+'X'.repeat(600));
 assert.equal(tooLong.query.get('admin'),'broadcast');
 assert.equal(tooLong.query.get('broadcast'),null);
 const empty=parseOriginalAdminCommand('/broadcast');
 assert.equal(empty.query.get('admin'),'broadcast');
});
