-- Exact replacement for the ORIGINAL admin manual publish button.
-- Only a verified Telegram admin can enqueue through saraf-original-admin.
-- Workers run ORIGINAL Python post implementations. No funds/customers touched.
create table if not exists public.saraf_original_manual_social_requests (
 id bigint generated always as identity primary key,
 admin_chat_id bigint not null check (admin_chat_id>0),
 idempotency_key text not null check (length(idempotency_key) between 16 and 120),
 state text not null default 'queued'
   check (state in ('queued','processing','done','partial','failed','needs_review')),
 facebook_state text not null default 'pending'
   check (facebook_state in ('pending','posted','failed','unknown')),
 instagram_state text not null default 'pending'
   check (instagram_state in ('pending','posted','failed','unknown')),
 created_at timestamptz not null default now(),
 started_at timestamptz,
 finished_at timestamptz,
 last_error text,
 constraint saraf_original_manual_social_idempotency
  unique (admin_chat_id,idempotency_key)
);
-- Prevent a second manual post while the first is queued or underway.
create unique index if not exists saraf_original_one_manual_post_per_admin
 on public.saraf_original_manual_social_requests (admin_chat_id)
 where state in ('queued','processing');
create index if not exists saraf_original_social_queue_order
 on public.saraf_original_manual_social_requests (created_at,id)
 where state='queued';
alter table public.saraf_original_manual_social_requests enable row level security;
revoke all on table public.saraf_original_manual_social_requests from public,anon,authenticated;
grant select,insert,update on table public.saraf_original_manual_social_requests to service_role;
revoke all on sequence public.saraf_original_manual_social_requests_id_seq
 from public,anon,authenticated;
grant usage,select on sequence public.saraf_original_manual_social_requests_id_seq to service_role;

create or replace function public.saraf_original_claim_manual_social()
returns table(request_id bigint,requested_by bigint)
language plpgsql security invoker set search_path='' as $$
begin
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

create or replace function public.saraf_original_finish_manual_social(
 p_id bigint,p_facebook text,p_instagram text,p_error text default null
) returns boolean
language plpgsql security invoker set search_path='' as $$
declare result_count integer;
begin
 if p_id is null or p_id<=0 or
    p_facebook not in ('posted','failed','unknown') or
    p_instagram not in ('posted','failed','unknown') then return false;end if;
 update public.saraf_original_manual_social_requests
 set state=case
  when p_facebook='posted' and p_instagram='posted' then 'done'
  when p_facebook='unknown' or p_instagram='unknown' then 'needs_review'
  when p_facebook='posted' or p_instagram='posted' then 'partial'
  else 'failed' end,
 facebook_state=p_facebook,instagram_state=p_instagram,
 finished_at=now(),last_error=left(coalesce(p_error,''),150)
 where id=p_id and state='processing';
 get diagnostics result_count=row_count;
 return result_count=1;
end;
$$;
revoke all on function public.saraf_original_claim_manual_social() from public,anon,authenticated;
revoke all on function public.saraf_original_finish_manual_social(bigint,text,text,text)
 from public,anon,authenticated;
grant execute on function public.saraf_original_claim_manual_social() to service_role;
grant execute on function public.saraf_original_finish_manual_social(bigint,text,text,text) to service_role;
