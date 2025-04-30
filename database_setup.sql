CREATE DATABASE IF NOT EXISTS student_performance_db;

USE student_performance_db;

CREATE TABLE IF NOT EXISTS students (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  roll_number VARCHAR(50) UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS subjects (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(50) UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS grades (
  id INT AUTO_INCREMENT PRIMARY KEY,
  roll_number VARCHAR(50),
  subject VARCHAR(50),
  grade INT,
  UNIQUE KEY unique_grade (roll_number, subject),
  FOREIGN KEY (roll_number) REFERENCES students(roll_number) ON DELETE CASCADE,
  FOREIGN KEY (subject) REFERENCES subjects(name) ON DELETE CASCADE
);

-- Insert default subjects
INSERT IGNORE INTO subjects (name) VALUES ('Math'), ('Science'), ('English');
