-- A crash/timeout after Meta accepts a post must NEVER auto-publish
-- again. Mark the request as needing human review after a safe timeout.
-- This uses original queue and state; all interactions stay service_role only.
create or replace function public.saraf_original_claim_manual_social()
returns table(request_id bigint,requested_by bigint)
language plpgsql security invoker set search_path='' as $$
begin
 update public.saraf_original_manual_social_requests
 set state='needs_review',
     facebook_state=case when facebook_state='pending' then 'unknown' else facebook_state end,
     instagram_state=case when instagram_state='pending' then 'unknown' else instagram_state end,
     finished_at=now(),last_error='WORKER_TIMED_OUT_REVIEW_META_BEFORE_RETRY'
 where state='processing' and started_at<now()-interval '15 minutes';
 return query
 with next as (
  select r.id from public.saraf_original_manual_social_requests r
  where r.state='queued'
  order by r.created_at,r.id
  for update skip locked limit 1
 )
 update public.saraf_original_manual_social_requests r
 set state='processing',started_at=now()
 from next where r.id=next.id
 returning r.id,r.admin_chat_id;
end;
$$;
revoke all on function public.saraf_original_claim_manual_social() from public,anon,authenticated;
grant execute on function public.saraf_original_claim_manual_social() to service_role;