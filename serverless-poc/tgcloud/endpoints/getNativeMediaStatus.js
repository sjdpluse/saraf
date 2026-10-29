import { actor } from '../lib/native_auth.js';
import { latestMedia } from '../lib/native_media.js';
export default async function(input,ctx) {
  const user=actor(ctx);
  const kind=String(input?.kind || 'RECEIPT').toUpperCase();
  const row=await latestMedia(user.id,kind);
  if (!row) return {ready:false};
  // No file_id or personal document is exposed to the browser.
  return {ready:true,id:row.id,receivedAt:row.receivedAt};
}
