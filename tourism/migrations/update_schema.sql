-- Migration script for enhanced admin panel with RBAC
-- Run this after backing up your database

USE daily_tourism;

-- ============================================
-- 1. Create audit_log table for action logging
-- ============================================
CREATE TABLE IF NOT EXISTS audit_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NULL,
    action VARCHAR(100) NOT NULL,
    resource VARCHAR(100) NOT NULL,
    details TEXT NULL,
    ip_address VARCHAR(45) NULL,
    user_agent VARCHAR(255) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id),
    INDEX idx_action (action),
    INDEX idx_resource (resource),
    INDEX idx_created_at (created_at),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- 2. Update users table with additional fields
-- ============================================
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS last_login DATETIME NULL,
ADD COLUMN IF NOT EXISTS created_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
ADD COLUMN IF NOT EXISTS updated_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP;

-- ============================================
-- 2.1 Add security fields for brute-force protection
-- ============================================
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS failed_login_attempts INT NOT NULL DEFAULT 0 AFTER last_login,
ADD COLUMN IF NOT EXISTS locked_until DATETIME NULL AFTER failed_login_attempts;

-- Create index for locked_until queries
CREATE INDEX IF NOT EXISTS idx_users_locked_until ON users(locked_until);

-- ============================================
-- 3. Ensure permissions tables exist
-- ============================================
CREATE TABLE IF NOT EXISTS permissions (
    user_id INT NOT NULL PRIMARY KEY,
    can_view_all BOOLEAN NOT NULL DEFAULT FALSE,
    can_export BOOLEAN NOT NULL DEFAULT FALSE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS permissions_subdivisions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    subdivision VARCHAR(255) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_user_subdivision (user_id, subdivision),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS permissions_otdels (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    otdel VARCHAR(255) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_user_otdel (user_id, otdel),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- 4. Create roles table for future expansion
-- ============================================
CREATE TABLE IF NOT EXISTS roles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    display_name VARCHAR(100) NOT NULL,
    description TEXT NULL,
    is_system BOOLEAN NOT NULL DEFAULT FALSE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- 5. Insert default roles
-- ============================================
INSERT IGNORE INTO roles (id, name, display_name, description, is_system) VALUES
(1, 'admin', 'Администратор', 'Полный доступ ко всем функциям системы', TRUE),
(2, 'manager', 'Менеджер', 'Доступ к данным с возможностью экспорта', TRUE),
(3, 'user', 'Пользователь', 'Базовый доступ только на просмотр', TRUE);

-- ============================================
-- 6. Update existing users with timestamps
-- ============================================
UPDATE users SET created_at = NOW() WHERE created_at IS NULL;
UPDATE users SET last_login = NOW() WHERE last_login IS NULL AND password_hash IS NOT NULL;

-- ============================================
-- 7. Grant necessary privileges (adjust as needed)
-- ============================================
-- GRANT SELECT, INSERT, UPDATE ON daily_tourism.audit_log TO 'your_user'@'localhost';

-- ============================================
-- 8. Verify the migration
-- ============================================
SELECT 'Migration completed successfully!' AS status;
SHOW TABLES;
SELECT COUNT(*) as audit_log_count FROM audit_log;
SELECT COUNT(*) as users_count FROM users;
