-- Migration script for brute-force protection
-- Run this after backing up your database

USE daily_tourism;

-- ============================================
-- Add security fields for brute-force protection
-- ============================================
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS failed_login_attempts INT NOT NULL DEFAULT 0 AFTER last_login,
ADD COLUMN IF NOT EXISTS locked_until DATETIME NULL AFTER failed_login_attempts;

-- Create index for locked_until queries (performance optimization)
CREATE INDEX IF NOT EXISTS idx_users_locked_until ON users(locked_until);

-- ============================================
-- Initialize existing users with default values
-- ============================================
UPDATE users SET failed_login_attempts = 0 WHERE failed_login_attempts IS NULL;

-- ============================================
-- Verify the migration
-- ============================================
SELECT 'Brute-force protection migration completed successfully!' AS status;
DESCRIBE users;
SELECT username, failed_login_attempts, locked_until FROM users LIMIT 5;
