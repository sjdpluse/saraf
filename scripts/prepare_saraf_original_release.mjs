// Prepare a strictly allowlisted Saraf ORIGINAL bot release WITHOUT cloning locally.
// Never copy financial/identity/admin native SQLite endpoints or native schema.
// Run AFTER: cd webapp && npm run build:telegram-original
import { cp, mkdir, readFile, rm, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const scriptDir=path.dirname(fileURLToPath(import.meta.url));
const root=path.resolve(scriptDir,'..');
const projectRoot=path.join(root,'serverless-poc');
const moduleSource=path.join(projectRoot,'tgcloud');
const target=path.join(projectRoot,'.release-original');
const originalBot='sarafiaf_bot';
const allowlist=Object.freeze([
  'handlers/message.js',
  'handlers/callback_query.js',
  'lib/legacy_menus.js',
  'lib/legacy_calc.js',
  'lib/legacy_rate_engine.js',
  'lib/legacy_compare.js',
  'lib/currencies.js',
  'lib/reference_rates.js',
  'lib/metals.js',
  'lib/cryptos.js',
  'lib/local_market_parser.js',
  'lib/local_market_service.js',
  'endpoints/getReadOnlyMarket.js',
  'endpoints/getLocalMarket.js',
  'endpoints/getMarketSnapshot.js',
  'endpoints/getSarafCapabilities.js',
]);
const selected=new Set(allowlist);

await rm(target,{recursive:true,force:true});
await mkdir(path.join(target,'tgcloud'),{recursive:true});
for(const item of allowlist){
  const source=path.join(moduleSource,item);
  const text=await readFile(source,'utf8');
  if(text.includes('service_role') || text.includes('SUPABASE_SERVICE_ROLE_KEY') ||
    text.includes('PUBLIC_DEPOSIT_WALLETS') || /\b(?:db|nativeOrders|nativeRemittances)\b/.test(text)){
    throw new Error('Disallowed financial, secret or database reference: '+item);
  }
  // A deploy must not silently omit a dependency used by a handler/endpoint.
  const imports=[...text.matchAll(/from\s+['"]([^'"]+)['"]/g)].map(x=>x[1]);
  for(const imp of imports){
    if(imp==='sdk')continue;
    if(!imp.startsWith('.')) throw new Error('Unsupported runtime dependency: '+item+' => '+imp);
    const normalized=path.posix.normalize(path.posix.join(path.posix.dirname(item),imp));
    if(!selected.has(normalized))throw new Error('Dependency not on allowlist: '+item+' => '+normalized);
  }
  const dest=path.join(target,'tgcloud',item);
  await mkdir(path.dirname(dest),{recursive:true});
  await writeFile(dest,text,'utf8');
}
const built=path.join(projectRoot,'dist');
await readFile(path.join(built,'index.html'),'utf8');
await cp(built,path.join(target,'dist'),{recursive:true});
await writeFile(path.join(target,'tgcloud.jsonc'),JSON.stringify({
  $schema:'./node_modules/@tgcloud/cli/schema/tgcloud.json',
  static:{
    source:'dist',
    immutable:['/assets/*'],
    spa:true,
    headers:[{path:'/*',set:{'Referrer-Policy':'no-referrer'}}],
  },
},null,2)+'\n');
await writeFile(path.join(target,'package.json'),JSON.stringify({
  name:'saraf-original-serverless-readonly',
  private:true,
  version:'0.1.0',
  type:'module',
  devDependencies:{'@tgcloud/cli':'0.2.0'},
},null,2)+'\n');
await writeFile(path.join(target,'RELEASE_SCOPE.txt'),
  'TARGET ORIGINAL TELEGRAM BOT: @'+originalBot+'\n'
  +'MODE: read-only reference markets and Supabase-history React frontend\n'
  +'DO NOT MIGRATE TELEGRAM SQLITE: no native schema.js included\n'
  +'NO MONEY OR KYC WRITE HANDLERS INCLUDED\n'
  +'REQUIRES VERIFIED ORIGINAL-BOT CLI ACCESS TOKEN FROM BOTFATHER\n');
console.log('Prepared read-only ORIGINAL bot release for @'+originalBot);
console.log('Modules:',allowlist.length,'(no native SQLite schema or financial endpoints)');
console.log('Release location: serverless-poc/.release-original');
