// Telegram-native Saraf tables. Separate from legacy Supabase; do NOT treat
// existing customers or historic orders as migrated until reconciled.
import { table, integer, text, index, uniqueIndex } from 'sdk/db';

export const smokeCounters = table('saraf_poc_counters', {
  chatId: integer('chat_id').primaryKey(),
  seen: integer('seen').notNull().default(0),
});

export const sarafSettings = table('saraf_native_settings', {
  key: text('key').primaryKey(),
  value: text('value').notNull(),
  changedBy: integer('changed_by'),
  updatedAt: text('updated_at').notNull(),
});

export const nativeProfiles = table('saraf_native_profiles', {
  userId: integer('user_id').primaryKey(),
  username: text('username'),
  firstName: text('first_name'),
  lastName: text('last_name'),
  phone: text('phone'),
  kycStatus: text('kyc_status').notNull().default('pending'),
  idDocumentFileId: text('id_document_file_id'),
  selfieFileId: text('selfie_file_id'),
  paymentInfo: text('payment_info'),
  verifiedBy: integer('verified_by'),
  updatedAt: text('updated_at').notNull(),
});

export const nativeQuotes = table('saraf_native_quotes', {
  id: integer('id').primaryKey({ autoIncrement: true }),
  userId: integer('user_id').notNull(),
  action: text('action').notNull(),
  asset: text('asset').notNull(),
  amountCents: integer('amount_cents').notNull(),
  usdRateBasisPoints: integer('usd_rate_basis_points').notNull(),
  totalAfnTenth: integer('total_afn_tenth').notNull(),
  totalUsdCents: integer('total_usd_cents').notNull(),
  pricingJson: text('pricing_json').notNull(),
  source: text('source').notNull(),
  expiresAt: integer('expires_at').notNull(),
  status: text('status').notNull().default('active'),
  orderId: integer('order_id'),
  createdAt: text('created_at').notNull(),
}, (t) => ({
  ownerIdx: index('saraf_native_quotes_owner').on(t.userId),
}));

export const nativeOrders = table('saraf_native_orders', {
  id: integer('id').primaryKey({ autoIncrement: true }),
  userId: integer('user_id').notNull(),
  idempotencyKey: text('idempotency_key').notNull(),
  requestHash: text('request_hash').notNull(),
  quoteId: integer('quote_id').notNull().unique(),
  action: text('action').notNull(),
  asset: text('asset').notNull(),
  amountCents: integer('amount_cents').notNull(),
  afnTenth: integer('afn_tenth').notNull(),
  usdRateBasisPoints: integer('usd_rate_basis_points').notNull(),
  network: text('network').notNull(),
  exchangeName: text('exchange_name'),
  walletAddress: text('wallet_address'),
  paymentMethod: text('payment_method'),
  receiveMethod: text('receive_method'),
  bankInfo: text('bank_info'),
  inPersonCode: text('in_person_code'),
  receiptFileId: text('receipt_file_id'),
  transactionProof: text('transaction_proof'),
  status: text('status').notNull().default('pending'),
  rating: integer('rating'),
  ratingComment: text('rating_comment'),
  createdAt: text('created_at').notNull(),
  updatedAt: text('updated_at').notNull(),
}, (t) => ({
  idem: uniqueIndex('saraf_native_orders_idem').on(t.userId, t.idempotencyKey),
  ownerIdx: index('saraf_native_orders_owner').on(t.userId),
}));

export const nativeRemittances = table('saraf_native_remittances', {
  id: integer('id').primaryKey({ autoIncrement: true }),
  userId: integer('user_id').notNull(),
  idempotencyKey: text('idempotency_key').notNull(),
  requestHash: text('request_hash').notNull(),
  asset: text('asset').notNull(),
  network: text('network').notNull(),
  amountCents: integer('amount_cents').notNull(),
  payoutAfnTenth: integer('payout_afn_tenth').notNull(),
  rateBasisPoints: integer('rate_basis_points').notNull(),
  depositWallet: text('deposit_wallet').notNull(),
  senderName: text('sender_name').notNull(),
  senderCountry: text('sender_country').notNull(),
  beneficiaryName: text('beneficiary_name').notNull(),
  beneficiaryPhone: text('beneficiary_phone').notNull(),
  beneficiaryLocation: text('beneficiary_location').notNull(),
  beneficiaryDocumentFileId: text('beneficiary_document_file_id'),
  txHash: text('tx_hash'),
  verificationStatus: text('verification_status').notNull().default('unverified'),
  status: text('status').notNull().default('awaiting_transfer'),
  createdAt: text('created_at').notNull(),
  updatedAt: text('updated_at').notNull(),
}, (t) => ({
  idem: uniqueIndex('saraf_native_remit_idem').on(t.userId, t.idempotencyKey),
  ownerIdx: index('saraf_native_remit_owner').on(t.userId),
  txUnique: uniqueIndex('saraf_native_remit_tx').on(t.network, t.txHash),
}));

export const nativeReviews = table('saraf_native_reviews', {
  id: integer('id').primaryKey({ autoIncrement: true }),
  userId: integer('user_id').notNull(),
  displayName: text('display_name').notNull(),
  body: text('body').notNull(),
  adminReply: text('admin_reply'),
  adminRepliedAt: text('admin_replied_at'),
  visible: integer('visible').notNull().default(1),
  createdAt: text('created_at').notNull(),
}, (t) => ({
  recentIdx: index('saraf_native_reviews_recent').on(t.createdAt),
}));

export const nativeVotes = table('saraf_native_votes', {
  reviewId: integer('review_id').notNull(),
  userId: integer('user_id').notNull(),
  vote: integer('vote').notNull(),
  updatedAt: text('updated_at').notNull(),
}, (t) => ({
  once: uniqueIndex('saraf_native_votes_once').on(t.reviewId, t.userId),
}));

export const nativeAudit = table('saraf_native_audit', {
  id: integer('id').primaryKey({ autoIncrement: true }),
  action: text('action').notNull(),
  entityType: text('entity_type').notNull(),
  entityId: integer('entity_id'),
  actorId: integer('actor_id').notNull(),
  beforeJson: text('before_json'),
  afterJson: text('after_json'),
  at: text('at').notNull(),
}, (t) => ({
  byEntity: index('saraf_native_audit_by_entity').on(t.entityType, t.entityId),
}));

export const nativeMedia = table('saraf_native_media', {
  id: integer('id').primaryKey({ autoIncrement: true }),
  userId: integer('user_id').notNull(),
  kind: text('kind').notNull(),
  telegramFileId: text('telegram_file_id').notNull(),
  mimeType: text('mime_type').notNull(),
  mediaCategory: text('media_category').notNull().default('photo'),
  telegramMessageId: integer('telegram_message_id').notNull(),
  receivedAt: text('received_at').notNull(),
  claimedBy: text('claimed_by'),
}, (t) => ({
  byUser: index('saraf_native_media_by_user').on(t.userId, t.kind),
  uniqueMessage: uniqueIndex('saraf_native_media_msg_once').on(t.userId, t.telegramMessageId),
}));
