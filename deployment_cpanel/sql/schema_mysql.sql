-- Schema MySQL pentru aplicația de analize medicale
-- Rulează acest script pentru a crea tabelele în MySQL

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- Tabel pacienti
CREATE TABLE IF NOT EXISTS `pacienti` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `cnp` VARCHAR(13) NOT NULL UNIQUE,
  `nume` VARCHAR(100) NOT NULL,
  `prenume` VARCHAR(100) DEFAULT '',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_cnp (cnp),
  INDEX idx_nume (nume)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Tabel analiza_standard
CREATE TABLE IF NOT EXISTS `analiza_standard` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `cod` VARCHAR(50) UNIQUE,
  `denumire` VARCHAR(200) NOT NULL,
  `categorie` VARCHAR(100),
  `unitate_std` VARCHAR(20),
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_cod (cod),
  INDEX idx_denumire (denumire)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Tabel analiza_alias
CREATE TABLE IF NOT EXISTS `analiza_alias` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `analiza_standard_id` INT NOT NULL,
  `alias` VARCHAR(200) NOT NULL,
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (analiza_standard_id) REFERENCES analiza_standard(id) ON DELETE CASCADE,
  INDEX idx_alias (alias)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Tabel analiza_necunoscuta
CREATE TABLE IF NOT EXISTS `analiza_necunoscuta` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `denumire_raw` VARCHAR(300) NOT NULL UNIQUE,
  `aparitii` INT DEFAULT 1,
  `aprobata` BOOLEAN DEFAULT FALSE,
  `analiza_standard_id` INT,
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (analiza_standard_id) REFERENCES analiza_standard(id) ON DELETE SET NULL,
  INDEX idx_denumire (denumire_raw),
  INDEX idx_aprobata (aprobata)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Tabel buletine
CREATE TABLE IF NOT EXISTS `buletine` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `pacient_id` INT NOT NULL,
  `data_buletin` VARCHAR(20),
  `laborator` VARCHAR(100),
  `fisier_original` VARCHAR(255),
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (pacient_id) REFERENCES pacienti(id) ON DELETE CASCADE,
  INDEX idx_pacient (pacient_id),
  INDEX idx_data (data_buletin)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Tabel rezultate_analize
CREATE TABLE IF NOT EXISTS `rezultate_analize` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `buletin_id` INT NOT NULL,
  `analiza_standard_id` INT,
  `denumire_raw` VARCHAR(300),
  `valoare` DECIMAL(12,4),
  `valoare_text` TEXT,
  `unitate` VARCHAR(50),
  `interval_min` DECIMAL(12,4),
  `interval_max` DECIMAL(12,4),
  `flag` VARCHAR(10),
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (buletin_id) REFERENCES buletine(id) ON DELETE CASCADE,
  FOREIGN KEY (analiza_standard_id) REFERENCES analiza_standard(id) ON DELETE SET NULL,
  INDEX idx_buletin (buletin_id),
  INDEX idx_analiza (analiza_standard_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET FOREIGN_KEY_CHECKS = 1;
