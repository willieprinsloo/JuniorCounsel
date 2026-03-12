-- Junior Counsel Test Data Seeding
-- Migration 002: Insert test data for development/testing
-- Created: 2026-03-12

-- ============================================================
-- TEST ORGANISATION & USERS
-- ============================================================

-- Insert test organisation
INSERT INTO organisations (id, name, contact_email, is_active) VALUES
(1, 'Test Law Firm', 'contact@testlawfirm.co.za', TRUE);

-- Insert test users
-- Password: 'password123' (hashed with werkzeug.security)
-- Hash generated with: from werkzeug.security import generate_password_hash; print(generate_password_hash('password123'))
INSERT INTO users (id, email, password_hash, full_name, is_active) VALUES
(1, 'advocate@testlawfirm.co.za', 'pbkdf2:sha256:600000$randomsalt$hash', 'Test Advocate', TRUE),
(2, 'attorney@testlawfirm.co.za', 'pbkdf2:sha256:600000$randomsalt$hash', 'Test Attorney', TRUE);

-- Link users to organisation
INSERT INTO organisation_users (organisation_id, user_id, role) VALUES
(1, 1, 'practitioner'),
(1, 2, 'practitioner');

-- ============================================================
-- TEST RULEBOOKS
-- ============================================================

-- Insert sample rulebooks (simplified YAML)
INSERT INTO rulebooks (document_type, jurisdiction, version, label, status, source_yaml, rules_json) VALUES
(
    'affidavit_founding',
    'High Court - Gauteng Division',
    '1.0.0',
    'Founding Affidavit Template v1.0',
    'published',
    '# Founding Affidavit Rulebook
document_type: affidavit_founding
jurisdiction: High Court - Gauteng Division
version: 1.0.0',
    '{"document_type": "affidavit_founding", "jurisdiction": "High Court - Gauteng Division", "version": "1.0.0"}'::jsonb
),
(
    'pleading_particulars_of_claim',
    'High Court - Gauteng Division',
    '1.0.0',
    'Particulars of Claim Template v1.0',
    'published',
    '# Particulars of Claim Rulebook
document_type: pleading_particulars_of_claim
jurisdiction: High Court - Gauteng Division
version: 1.0.0',
    '{"document_type": "pleading_particulars_of_claim", "jurisdiction": "High Court - Gauteng Division", "version": "1.0.0"}'::jsonb
);

-- ============================================================
-- SEQUENCE RESETS
-- ============================================================

-- Reset sequences to allow auto-increment after manual inserts
SELECT setval('organisations_id_seq', (SELECT MAX(id) FROM organisations));
SELECT setval('users_id_seq', (SELECT MAX(id) FROM users));
SELECT setval('organisation_users_id_seq', (SELECT MAX(id) FROM organisation_users));
SELECT setval('rulebooks_id_seq', (SELECT MAX(id) FROM rulebooks));

-- ============================================================
-- COMPLETION
-- ============================================================

SELECT 'Migration 002: Test data seeded successfully' AS status;
SELECT 'Test users: advocate@testlawfirm.co.za / attorney@testlawfirm.co.za' AS credentials;
SELECT 'Test password: password123 (you must hash this before use)' AS password_note;
