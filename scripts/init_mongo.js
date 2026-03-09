// MongoDB initialization script
// Runs on first container start via docker-entrypoint-initdb.d

db = db.getSiblingDB("compmon");

// Create collections
db.createCollection("snapshots");
db.createCollection("diffs");
db.createCollection("analyses");
db.createCollection("digest_queue");

// Snapshots indexes
db.snapshots.createIndex({ monitor_id: 1, created_at: -1 });
db.snapshots.createIndex({ text_hash: 1 });
db.snapshots.createIndex({ created_at: 1 }, { expireAfterSeconds: 90 * 24 * 60 * 60 }); // 90 day TTL

// Diffs indexes
db.diffs.createIndex({ monitor_id: 1, created_at: -1 });
db.diffs.createIndex({ is_empty_after_filter: 1 });
db.diffs.createIndex({ created_at: 1 }, { expireAfterSeconds: 180 * 24 * 60 * 60 }); // 180 day TTL

// Analyses indexes
db.analyses.createIndex({ monitor_id: 1, created_at: -1 });
db.analyses.createIndex({ diff_id: 1 }, { unique: true });
db.analyses.createIndex({ significance_level: 1 });
db.analyses.createIndex({ needs_review: 1 });
db.analyses.createIndex({ created_at: 1 }, { expireAfterSeconds: 365 * 24 * 60 * 60 }); // 365 day TTL

// Digest queue indexes
db.digest_queue.createIndex({ sent: 1, scheduled_for: 1 });
db.digest_queue.createIndex({ user_id: 1 });

print("MongoDB initialization complete: collections and indexes created.");
