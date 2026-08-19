create table if not exists public.fb_comment_events (
    comment_id text primary key,
    post_id text,
    parent_id text,
    from_id text,
    from_name text,
    message text not null default '',
    replied boolean not null default false,
    created_at timestamptz not null default now(),
    processed_at timestamptz
);

create index if not exists idx_fb_comment_events_post_created
    on public.fb_comment_events (post_id, created_at desc);

create index if not exists idx_fb_comment_events_from_created
    on public.fb_comment_events (from_id, created_at desc);

alter table public.fb_comment_events enable row level security;
