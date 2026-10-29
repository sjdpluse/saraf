import { actor } from '../lib/native_auth.js';
import { getOwnRemittances } from '../lib/native_remittances.js';
export default async function(_input,ctx){return getOwnRemittances(actor(ctx).id);}
