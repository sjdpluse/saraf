-- Like/dislike votes for Mini App reviews.
create table if not exists public.miniapp_review_votes (
    review_id bigint not null references public.miniapp_reviews(id) on delete cascade,
    chat_id bigint not null,
    vote smallint not null check (vote in (-1, 1)),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    primary key (review_id, chat_id)
);

create index if not exists miniapp_review_votes_review_idx
    on public.miniapp_review_votes (review_id, vote);

alter table public.miniapp_review_votes enable row level security;
