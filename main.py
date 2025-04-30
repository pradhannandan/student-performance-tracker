from flask import Flask, render_template, request, redirect, url_for, flash
import mysql.connector
from mysql.connector import Error

app = Flask(__name__)
app.secret_key = 'd3f4a1b2c5e67890f1a2b3c4d5e6f789'  

# Object-Oriented Design: Student and StudentTracker classes
class Student:
    def __init__(self, name, roll_number):
        self.name = name
        self.roll_number = roll_number
        self.grades = {}  # subject: grade

    def add_grade(self, subject, grade):
        if 0 <= grade <= 100:
            self.grades[subject] = grade
        else:
            raise ValueError("Grade must be between 0 and 100")

    def average_grade(self):
        if not self.grades:
            return None
        return sum(self.grades.values()) / len(self.grades)

    def display_info(self):
        return {
            'name': self.name,
            'roll_number': self.roll_number,
            'grades': self.grades,
            'average': self.average_grade()
        }

class StudentTracker:
    def __init__(self):
        self.students = {}  # roll_number: Student object

    def add_student(self, name, roll_number):
        if roll_number in self.students:
            raise ValueError("Roll number already exists")
        self.students[roll_number] = Student(name, roll_number)

    def add_grades(self, roll_number, grades):
        if roll_number not in self.students:
            raise ValueError("Student not found")
        for subject, grade in grades.items():
            self.students[roll_number].add_grade(subject, grade)

    def view_student_details(self, roll_number):
        if roll_number not in self.students:
            return None
        return self.students[roll_number].display_info()

    def calculate_average(self, roll_number):
        if roll_number not in self.students:
            return None
        return self.students[roll_number].average_grade()

    def get_all_students(self):
        return list(self.students.values())

import os

# MySQL database configuration using environment variables
db_config = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME', 'student_performance_db') 
}

def get_db_connection():
    try:
        connection = mysql.connector.connect(**db_config)
        return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/add_student', methods=['GET', 'POST'])
def add_student():
    if request.method == 'POST':
        name = request.form['name']
        roll_number = request.form['roll_number']

        if not name or not roll_number:
            flash('Please enter both name and roll number.')
            return redirect(url_for('add_student'))

        connection = get_db_connection()
        if connection:
            cursor = connection.cursor()
            # Check if roll_number is unique
            cursor.execute("SELECT * FROM students WHERE roll_number = %s", (roll_number,))
            existing_student = cursor.fetchone()
            if existing_student:
                flash('Roll number already exists. Please use a unique roll number.')
                cursor.close()
                connection.close()
                return redirect(url_for('add_student'))

            cursor.execute("INSERT INTO students (name, roll_number) VALUES (%s, %s)", (name, roll_number))
            connection.commit()
            cursor.close()
            connection.close()
            flash('Student added successfully!')
            return redirect(url_for('index'))
        else:
            flash('Database connection error.')
            return redirect(url_for('add_student'))
    return render_template('add_student.html')

@app.route('/update_student/<roll_number>', methods=['GET', 'POST'])
def update_student(roll_number):
    connection = get_db_connection()
    if not connection:
        flash('Database connection error.')
        return redirect(url_for('index'))

    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM students WHERE roll_number = %s", (roll_number,))
    student = cursor.fetchone()
    if not student:
        cursor.close()
        connection.close()
        flash('Student not found.')
        return redirect(url_for('index'))

    if request.method == 'POST':
        new_name = request.form['name']
        new_roll_number = request.form['roll_number']

        if not new_name or not new_roll_number:
            flash('Please enter both name and roll number.')
            return redirect(url_for('update_student', roll_number=roll_number))

        # Check if new roll number is unique or same as current
        cursor.execute("SELECT * FROM students WHERE roll_number = %s AND roll_number != %s", (new_roll_number, roll_number))
        existing_student = cursor.fetchone()
        if existing_student:
            flash('Roll number already exists. Please use a unique roll number.')
            cursor.close()
            connection.close()
            return redirect(url_for('update_student', roll_number=roll_number))

        # Update student details
        cursor.execute("UPDATE students SET name = %s, roll_number = %s WHERE roll_number = %s", (new_name, new_roll_number, roll_number))
        connection.commit()
        cursor.close()
        connection.close()
        flash('Student details updated successfully!')
        return redirect(url_for('view_student'))

    cursor.close()
    connection.close()
    return render_template('update_student.html', student=student)

import re

def sanitize_subject(subject):
    return re.sub(r'\W+', '_', subject.lower())

@app.route('/add_grades', methods=['GET', 'POST'])
def add_grades():
    connection = get_db_connection()
    if not connection:
        flash('Database connection error.')
        return redirect(url_for('index'))

    cursor = connection.cursor()
    cursor.execute("SELECT name FROM subjects")
    subjects = [row[0] for row in cursor.fetchall()]
    cursor.close()
    connection.close()

    if request.method == 'POST':
        roll_number = request.form['roll_number']
        grades = {}
        try:
            for subject in subjects:
                field_name = sanitize_subject(subject)
                grade_str = request.form.get(field_name, '').strip()
                if grade_str == '':
                    flash(f'Grade for {subject} is required.')
                    return redirect(url_for('add_grades'))
                grades[subject] = int(grade_str)
        except ValueError:
            flash('Grades must be valid integers.')
            return redirect(url_for('add_grades'))

        # Validate grades range
        for grade in grades.values():
            if grade < 0 or grade > 100:
                flash('Grades must be between 0 and 100.')
                return redirect(url_for('add_grades'))

        connection = get_db_connection()
        if connection:
            cursor = connection.cursor()
            # Check if student exists
            cursor.execute("SELECT * FROM students WHERE roll_number = %s", (roll_number,))
            student = cursor.fetchone()
            if not student:
                flash('Student with this roll number does not exist.')
                cursor.close()
                connection.close()
                return redirect(url_for('add_grades'))

            # Insert or update grades
            for subject, grade in grades.items():
                cursor.execute("""
                    INSERT INTO grades (roll_number, subject, grade)
                    VALUES (%s, %s, %s)
                    ON DUPLICATE KEY UPDATE grade = VALUES(grade)
                """, (roll_number, subject, grade))
            connection.commit()
            cursor.close()
            connection.close()
            flash('Grades added/updated successfully!')
            return redirect(url_for('index'))
        else:
            flash('Database connection error.')
            return redirect(url_for('add_grades'))
    return render_template('add_grades.html', subjects=subjects, sanitize_subject=sanitize_subject)

@app.route('/view_student', methods=['GET', 'POST'])
def view_student():
    if request.method == 'GET':
        return render_template('view_student_form.html')

    student = None
    grades = {'Math': None, 'Science': None, 'English': None}
    average = None

    if request.method == 'POST':
        roll_number = request.form['roll_number']
        connection = get_db_connection()
        if connection:
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT * FROM students WHERE roll_number = %s", (roll_number,))
            student = cursor.fetchone()
            if student:
                cursor.execute("SELECT subject, grade FROM grades WHERE roll_number = %s", (roll_number,))
                grade_rows = cursor.fetchall()
                for row in grade_rows:
                    grades[row['subject']] = row['grade']
                # Calculate average if grades exist
                valid_grades = [g for g in grades.values() if g is not None]
                if valid_grades:
                    average = sum(valid_grades) / len(valid_grades)
            cursor.close()
            connection.close()
        else:
            flash('Database connection error.')

    return render_template('view_student.html', student=student, grades=grades, average=average)

@app.route('/delete_student/<roll_number>', methods=['POST'])
def delete_student(roll_number):
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor()
        # Delete student and cascade delete grades
        cursor.execute("DELETE FROM students WHERE roll_number = %s", (roll_number,))
        connection.commit()
        cursor.close()
        connection.close()
        flash(f'Student with roll number {roll_number} deleted successfully.')
    else:
        flash('Database connection error.')
    return redirect(url_for('index'))

@app.route('/class_summary')
def class_summary():
    connection = get_db_connection()
    if not connection:
        flash('Database connection error.')
        return redirect(url_for('index'))

    cursor = connection.cursor(dictionary=True)
    # Get all subjects
    cursor.execute("SELECT DISTINCT subject FROM grades")
    subjects = [row['subject'] for row in cursor.fetchall()]

    # Calculate average marks per subject
    avg_per_subject = {}
    for subject in subjects:
        cursor.execute("SELECT AVG(grade) as avg_grade FROM grades WHERE subject = %s", (subject,))
        avg_per_subject[subject] = round(cursor.fetchone()['avg_grade'] or 0, 2)

    # Calculate average marks per student
    cursor.execute("""
        SELECT s.roll_number, s.name, AVG(g.grade) as avg_grade
        FROM students s
        LEFT JOIN grades g ON s.roll_number = g.roll_number
        GROUP BY s.roll_number, s.name
        ORDER BY avg_grade DESC
    """)
    student_averages = cursor.fetchall()
    # Replace None avg_grade with 0
    for student in student_averages:
        if student['avg_grade'] is None:
            student['avg_grade'] = 0

    # Identify topper(s)
    topper = student_averages[0] if student_averages else None

    # Calculate subject-wise toppers
    subject_toppers = {}
    for subject in subjects:
        cursor.execute("""
            SELECT s.name, s.roll_number, g.grade
            FROM grades g
            JOIN students s ON g.roll_number = s.roll_number
            WHERE g.subject = %s
            ORDER BY g.grade DESC
            LIMIT 1
        """, (subject,))
        result = cursor.fetchone()
        if result:
            subject_toppers[subject] = result
        else:
            subject_toppers[subject] = None

    cursor.close()
    connection.close()

    return render_template('class_summary.html', subjects=subjects, avg_per_subject=avg_per_subject,
                           student_averages=student_averages, topper=topper, subject_toppers=subject_toppers)

from flask import jsonify

@app.route('/manage_subjects', methods=['GET', 'POST'])
def manage_subjects():
    connection = get_db_connection()
    if not connection:
        flash('Database connection error.')
        return redirect(url_for('index'))

    cursor = connection.cursor()
    if request.method == 'POST':
        if 'add_subject' in request.form:
            new_subject = request.form['new_subject'].strip()
            if new_subject:
                try:
                    cursor.execute("INSERT INTO subjects (name) VALUES (%s)", (new_subject,))
                    connection.commit()
                    flash(f'Subject "{new_subject}" added successfully.')
                except mysql.connector.IntegrityError:
                    flash(f'Subject "{new_subject}" already exists.')
            else:
                flash('Subject name cannot be empty.')
        elif 'delete_subject' in request.form:
            subject_to_delete = request.form['delete_subject']
            cursor.execute("DELETE FROM subjects WHERE name = %s", (subject_to_delete,))
            connection.commit()
            flash(f'Subject "{subject_to_delete}" deleted successfully.')
        elif 'update_subject' in request.form:
            old_subject = request.form['old_subject']
            new_subject = request.form['new_subject_name'].strip()
            if not new_subject:
                flash('New subject name cannot be empty.')
            else:
                try:
                    # Update subject name in subjects table
                    cursor.execute("UPDATE subjects SET name = %s WHERE name = %s", (new_subject, old_subject))
                    # Update subject name in grades table for all students
                    cursor.execute("UPDATE grades SET subject = %s WHERE subject = %s", (new_subject, old_subject))
                    connection.commit()
                    flash(f'Subject "{old_subject}" renamed to "{new_subject}" successfully.')
                except mysql.connector.IntegrityError:
                    flash(f'Subject "{new_subject}" already exists.')

    cursor.execute("SELECT name FROM subjects ORDER BY name")
    subjects = [row[0] for row in cursor.fetchall()]
    cursor.close()
    connection.close()

    return render_template('manage_subjects.html', subjects=subjects)

@app.route('/update_grade/<roll_number>/<subject>', methods=['GET', 'POST'])
def update_grade(roll_number, subject):
    connection = get_db_connection()
    if not connection:
        flash('Database connection error.')
        return redirect(url_for('index'))

    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM students WHERE roll_number = %s", (roll_number,))
    student = cursor.fetchone()
    if not student:
        cursor.close()
        connection.close()
        flash('Student not found.')
        return redirect(url_for('index'))

    cursor.execute("SELECT grade FROM grades WHERE roll_number = %s AND subject = %s", (roll_number, subject))
    grade_row = cursor.fetchone()
    current_grade = grade_row['grade'] if grade_row else None

    if request.method == 'POST':
        try:
            new_grade = int(request.form['grade'])
            if new_grade < 0 or new_grade > 100:
                flash('Grade must be between 0 and 100.')
                return redirect(url_for('update_grade', roll_number=roll_number, subject=subject))
        except ValueError:
            flash('Invalid grade value.')
            return redirect(url_for('update_grade', roll_number=roll_number, subject=subject))

        cursor.execute("""
            INSERT INTO grades (roll_number, subject, grade)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE grade = VALUES(grade)
        """, (roll_number, subject, new_grade))
        connection.commit()
        cursor.close()
        connection.close()
        flash(f'Grade for {subject} updated successfully for student {student["name"]}.')
        return redirect(url_for('view_student'))

    cursor.close()
    connection.close()
    return render_template('update_grade.html', student=student, subject=subject, current_grade=current_grade)

from urllib.parse import unquote

@app.route('/update_student_subject/<roll_number>/<path:old_subject>', methods=['GET', 'POST'])
def update_student_subject(roll_number, old_subject):
    old_subject = unquote(old_subject)
    try:
        connection = get_db_connection()
        if not connection:
            flash('Database connection error.')
            return redirect(url_for('index'))

        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM students WHERE roll_number = %s", (roll_number,))
        student = cursor.fetchone()
        if not student:
            cursor.close()
            connection.close()
            flash('Student not found.')
            return redirect(url_for('index'))

        cursor.execute("SELECT subject FROM grades WHERE roll_number = %s AND subject = %s", (roll_number, old_subject))
        grade_row = cursor.fetchone()
        if not grade_row:
            cursor.close()
            connection.close()
            flash(f'No grade record found for subject {old_subject} for this student.')
            return redirect(url_for('view_student'))

        if request.method == 'POST':
            new_subject = request.form['new_subject'].strip()
            if not new_subject:
                flash('New subject name cannot be empty.')
                return redirect(url_for('update_student_subject', roll_number=roll_number, old_subject=old_subject))

            # Check if new subject already exists for this student
            cursor.execute("SELECT * FROM grades WHERE roll_number = %s AND subject = %s", (roll_number, new_subject))
            existing = cursor.fetchone()
            if existing:
                flash(f'This student already has a grade for subject "{new_subject}".')
                return redirect(url_for('update_student_subject', roll_number=roll_number, old_subject=old_subject))

            # Insert new subject for this student with NULL grade
            cursor.execute("INSERT INTO grades (roll_number, subject, grade) VALUES (%s, %s, NULL)", (roll_number, new_subject))
            connection.commit()
            cursor.close()
            connection.close()
            flash(f'New subject "{new_subject}" added for student {student["name"]}.')
            return redirect(url_for('view_student'))

        cursor.close()
        connection.close()
        return render_template('update_student_subject.html', student=student, old_subject=old_subject)
    except Exception as e:
        flash(f'Error updating subject: {str(e)}')
        return redirect(url_for('view_student'))

@app.route('/delete_student_subject/<roll_number>/<subject>', methods=['POST'])
def delete_student_subject(roll_number, subject):
    try:
        connection = get_db_connection()
        if not connection:
            flash('Database connection error.')
            return redirect(url_for('index'))

        cursor = connection.cursor()
        cursor.execute("DELETE FROM grades WHERE roll_number = %s AND subject = %s", (roll_number, subject))
        connection.commit()
        cursor.close()
        connection.close()
        flash(f'Subject "{subject}" deleted for student with roll number {roll_number}.')
        return redirect(url_for('view_student', roll_number=roll_number))
    except Exception as e:
        flash(f'Error deleting subject: {str(e)}')
        return redirect(url_for('index'))

    cursor.close()
    connection.close()
    return render_template('update_student_subject.html', student=student, old_subject=old_subject)

import os

@app.route('/export_data')
def export_data():
    connection = get_db_connection()
    if not connection:
        flash('Database connection error.')
        return redirect(url_for('index'))

    cursor = connection.cursor(dictionary=True)
    cursor.execute("""
        SELECT s.roll_number, s.name, g.subject, g.grade
        FROM students s
        LEFT JOIN grades g ON s.roll_number = g.roll_number
        ORDER BY s.roll_number, g.subject
    """)
    rows = cursor.fetchall()
    cursor.close()
    connection.close()

    # Prepare data for export
    data_lines = []
    current_roll = None
    for row in rows:
        if row['roll_number'] != current_roll:
            if current_roll is not None:
                data_lines.append("")  # blank line between students
            data_lines.append(f"Roll Number: {row['roll_number']}")
            data_lines.append(f"Name: {row['name']}")
            current_roll = row['roll_number']
        subject = row['subject'] if row['subject'] else "No Subject"
        grade = row['grade'] if row['grade'] is not None else "No Grade"
        data_lines.append(f"  {subject}: {grade}")

    export_path = os.path.join(os.getcwd(), "student_data_export.txt")
    with open(export_path, "w") as f:
        f.write("\n".join(data_lines))

    flash(f"Student data exported successfully to {export_path}")
    return redirect(url_for('index'))

if __name__ == '__main__':
    debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() in ['true', '1', 't']
    app.run(debug=debug_mode)
