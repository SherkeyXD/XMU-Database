from sqlalchemy import create_engine, Column, String, Integer, ForeignKey, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from dotenv import load_dotenv
from datetime import datetime
import hashlib
import os

Base = declarative_base()
load_dotenv()
conn_str = os.getenv("DB_CONN_STRING")


# 管理员表
class Admin(Base):
    __tablename__ = "admins"
    ano = Column(String(20), primary_key=True)
    aname = Column(String(20), nullable=False)
    password = Column(String(64), nullable=False)


# 学生表
class Student(Base):
    __tablename__ = "students"
    sno = Column(String(20), primary_key=True)
    sname = Column(String(20), nullable=False)
    smajor = Column(String(20), nullable=False)
    sclass = Column(String(20), nullable=True)
    sex = Column(String(10), nullable=True)
    birthday = Column(String(20), nullable=True)
    password = Column(String(64), nullable=False)
    grades = relationship("Grade", back_populates="student")


# 教师表
class Teacher(Base):
    __tablename__ = "teachers"
    tno = Column(String(20), primary_key=True)
    tname = Column(String(20), nullable=False)
    tdept = Column(String(50), nullable=True)
    password = Column(String(64), nullable=False)
    courses = relationship("Course", back_populates="teacher")


# 课程表
class Course(Base):
    __tablename__ = "courses"
    cno = Column(String(20), primary_key=True)
    cname = Column(String(50), nullable=False)
    credit = Column(Integer, nullable=False)
    tno = Column(String(20), ForeignKey("teachers.tno"))
    term = Column(String(20), nullable=True)
    teacher = relationship("Teacher", back_populates="courses")
    grades = relationship("Grade", back_populates="course")


# 成绩表
class Grade(Base):
    __tablename__ = "grades"
    id = Column(Integer, primary_key=True, autoincrement=True)
    sno = Column(String(20), ForeignKey("students.sno"))
    cno = Column(String(20), ForeignKey("courses.cno"))
    term = Column(String(20), nullable=False)
    grade = Column(Integer, nullable=True)
    student = relationship("Student", back_populates="grades")
    course = relationship("Course", back_populates="grades")


# 评论表（保留）
class Comment(Base):
    __tablename__ = "comments"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False)
    content = Column(String(500), nullable=False)
    timestamp = Column(DateTime, default=datetime.now)


class DatabaseManager:
    def __init__(self, database_url=conn_str):
        self.engine = create_engine(database_url)
        # 先清空所有表（开发环境用）
        Base.metadata.drop_all(self.engine)
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

        # 自动插入默认管理员账号
        if not self.session.query(Admin).first():
            default_admin = Admin(
                ano="admin", aname="超级管理员", password=self.hash_password("123456")
            )
            self.session.add(default_admin)
            self.session.commit()

    def hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()

    def verify_password(self, password, hashed):
        return self.hash_password(password) == hashed

    # ---------------- 管理员相关 ----------------
    def add_admin(self, ano, aname, password):
        try:
            if self.session.query(Admin).filter_by(ano=ano).first():
                return False, "管理员编号已存在"
            admin = Admin(ano=ano, aname=aname, password=self.hash_password(password))
            self.session.add(admin)
            self.session.commit()
            return True, "添加成功"
        except Exception as e:
            self.session.rollback()
            return False, f"添加失败: {str(e)}"

    def update_admin(self, ano, aname=None, password=None):
        try:
            admin = self.session.query(Admin).filter_by(ano=ano).first()
            if not admin:
                return False, "管理员不存在"
            if aname:
                admin.aname = aname
            if password:
                admin.password = self.hash_password(password)
            self.session.commit()
            return True, "更新成功"
        except Exception as e:
            self.session.rollback()
            return False, f"更新失败: {str(e)}"

    def delete_admin(self, ano):
        try:
            admin = self.session.query(Admin).filter_by(ano=ano).first()
            if not admin:
                return False, "管理员不存在"
            self.session.delete(admin)
            self.session.commit()
            return True, "删除成功"
        except Exception as e:
            self.session.rollback()
            return False, f"删除失败: {str(e)}"

    def get_admin(self, ano):
        return self.session.query(Admin).filter_by(ano=ano).first()

    def get_all_admins(self):
        return self.session.query(Admin).all()

    def admin_login(self, ano, password):
        admin = self.get_admin(ano)
        if admin and self.verify_password(password, admin.password):
            return True, admin
        return False, None

    def change_password(self, sno, old_password, new_password):
        student = self.get_student(sno)
        if not student or not self.verify_password(old_password, student.password):
            return False, "原密码错误"

        # 密码加密
        encrypted_new_password = self.hash_password(new_password)

        # 更新密码
        success = self.update_student_password(sno, encrypted_new_password)
        if success:
            return True, "密码修改成功"
        return False, "密码修改失败"

    # ---------------- 学生相关 ----------------
    def add_student(self, sno, sname, smajor, sclass, sex, birthday, password=None):
        try:
            if self.session.query(Student).filter_by(sno=sno).first():
                return False, "学号已存在"
            if not password:
                password = f"{sno}/123456"
            student = Student(
                sno=sno,
                sname=sname,
                smajor=smajor,
                sclass=sclass,
                sex=sex,
                birthday=birthday,
                password=self.hash_password(password),
            )
            self.session.add(student)
            self.session.commit()
            return True, "操作成功"
        except Exception as e:
            self.session.rollback()
            return False, f"操作失败: {str(e)}"

    def update_student(self, sno, **kwargs):
        try:
            student = self.session.query(Student).filter_by(sno=sno).first()
            if not student:
                return False, "学生不存在"
            for k, v in kwargs.items():
                if k == "password":
                    v = self.hash_password(v)
                setattr(student, k, v)
            self.session.commit()
            return True, "更新成功"
        except Exception as e:
            self.session.rollback()
            return False, f"更新失败: {str(e)}"

    def delete_student(self, sno):
        try:
            student = self.session.query(Student).filter_by(sno=sno).first()
            if not student:
                return False, "学生不存在"
            self.session.delete(student)
            self.session.commit()
            return True, "删除成功"
        except Exception as e:
            self.session.rollback()
            return False, f"删除失败: {str(e)}"

    def get_student(self, sno):
        return self.session.query(Student).filter_by(sno=sno).first()

    def get_all_students(self):
        return self.session.query(Student).all()

    def student_login(self, sno, password):
        student = self.get_student(sno)
        if student and self.verify_password(password, student.password):
            return True, student
        return False, None

    # ---------------- 教师相关 ----------------
    def add_teacher(self, tno, tname, tdept, password=None):
        try:
            if self.session.query(Teacher).filter_by(tno=tno).first():
                return False, "工号已存在"
            if not password:
                password = f"{tno}/123456"
            teacher = Teacher(
                tno=tno, tname=tname, tdept=tdept, password=self.hash_password(password)
            )
            self.session.add(teacher)
            self.session.commit()
            return True, "操作成功"
        except Exception as e:
            self.session.rollback()
            return False, f"操作失败: {str(e)}"

    def update_teacher(self, tno, **kwargs):
        try:
            teacher = self.session.query(Teacher).filter_by(tno=tno).first()
            if not teacher:
                return False, "教师不存在"
            for k, v in kwargs.items():
                if k == "password":
                    v = self.hash_password(v)
                setattr(teacher, k, v)
            self.session.commit()
            return True, "更新成功"
        except Exception as e:
            self.session.rollback()
            return False, f"更新失败: {str(e)}"

    def delete_teacher(self, tno):
        try:
            teacher = self.session.query(Teacher).filter_by(tno=tno).first()
            if not teacher:
                return False, "教师不存在"
            self.session.delete(teacher)
            self.session.commit()
            return True, "删除成功"
        except Exception as e:
            self.session.rollback()
            return False, f"删除失败: {str(e)}"

    def get_teacher(self, tno):
        return self.session.query(Teacher).filter_by(tno=tno).first()

    def get_all_teachers(self):
        return self.session.query(Teacher).all()

    def teacher_login(self, tno, password):
        teacher = self.get_teacher(tno)
        if teacher and self.verify_password(password, teacher.password):
            return True, teacher
        return False, None

    # ---------------- 课程相关 ----------------
    def add_course(self, cno, cname, credit, tno, term=None):
        try:
            if self.session.query(Course).filter_by(cno=cno).first():
                return False, "课程编号已存在"
            if not self.get_teacher(tno):
                return False, "教师不存在"
            course = Course(cno=cno, cname=cname, credit=credit, tno=tno, term=term)
            self.session.add(course)
            self.session.commit()
            return True, "添加成功"
        except Exception as e:
            self.session.rollback()
            return False, f"添加失败: {str(e)}"

    def update_course(self, cno, **kwargs):
        try:
            course = self.session.query(Course).filter_by(cno=cno).first()
            if not course:
                return False, "课程不存在"
            for k, v in kwargs.items():
                setattr(course, k, v)
            self.session.commit()
            return True, "更新成功"
        except Exception as e:
            self.session.rollback()
            return False, f"更新失败: {str(e)}"

    def delete_course(self, cno):
        try:
            course = self.session.query(Course).filter_by(cno=cno).first()
            if not course:
                return False, "课程不存在"
            self.session.delete(course)
            self.session.commit()
            return True, "删除成功"
        except Exception as e:
            self.session.rollback()
            return False, f"删除失败: {str(e)}"

    def get_course(self, cno):
        return self.session.query(Course).filter_by(cno=cno).first()

    def get_all_courses(self):
        return self.session.query(Course).all()

    # ---------------- 成绩相关 ----------------
    def add_grade(self, sno, cno, term, grade):
        try:
            if not self.get_student(sno):
                return False, "学生不存在"
            if not self.get_course(cno):
                return False, "课程不存在"
            grade_obj = Grade(sno=sno, cno=cno, term=term, grade=grade)
            self.session.add(grade_obj)
            self.session.commit()
            return True, "成绩添加成功"
        except Exception as e:
            self.session.rollback()
            return False, f"添加失败: {str(e)}"

    def update_grade(self, grade_id, grade):
        try:
            grade_obj = self.session.query(Grade).filter_by(id=grade_id).first()
            if not grade_obj:
                return False, "成绩记录不存在"
            grade_obj.grade = grade
            self.session.commit()
            return True, "成绩更新成功"
        except Exception as e:
            self.session.rollback()
            return False, f"更新失败: {str(e)}"

    def delete_grade(self, grade_id):
        try:
            grade_obj = self.session.query(Grade).filter_by(id=grade_id).first()
            if not grade_obj:
                return False, "成绩记录不存在"
            self.session.delete(grade_obj)
            self.session.commit()
            return True, "删除成功"
        except Exception as e:
            self.session.rollback()
            return False, f"删除失败: {str(e)}"

    def get_grade(self, grade_id):
        return self.session.query(Grade).filter_by(id=grade_id).first()

    def get_grades_by_student(self, sno, term=None, cno=None):
        # 先查询成绩表中该学生的成绩记录
        query = self.session.query(Grade).filter_by(sno=sno)

        # 如果提供了学期，添加学期过滤条件
        if term:
            query = query.filter_by(term=term)

        # 如果提供了课程编号，添加课程编号过滤条件
        if cno:
            query = query.filter_by(cno=cno)

        # 执行查询，获取学生的所有成绩记录
        grades = query.all()

        # 获取成绩对应的课程信息（课程名和学分）
        courses_and_credits = []
        for grade in grades:
            course = self.session.query(Course).filter_by(cno=grade.cno).first()
            if course:
                courses_and_credits.append(
                    {
                        "course_name": course.cname,  # 课程名称
                        "credits": course.credit,  # 学分
                        "grade": grade.grade,  # 成绩
                        "term": grade.term,  # 学期
                    }
                )

        return courses_and_credits

    def get_grades_by_teacher(self, tno, term=None, cno=None, sno=None):
        # 查询该教师所授课程的成绩
        courses = self.session.query(Course).filter_by(tno=tno).all()
        cnos = [c.cno for c in courses]
        query = self.session.query(Grade).filter(Grade.cno.in_(cnos))
        if term:
            query = query.filter_by(term=term)
        if cno:
            query = query.filter_by(cno=cno)
        if sno:
            query = query.filter_by(sno=sno)
        return query.all()

    def get_all_grades(self):
        return self.session.query(Grade).all()

    # ---------------- 评论相关（保留） ----------------
    def add_comment(self, name, content):
        try:
            comment = Comment(name=name, content=content)
            self.session.add(comment)
            self.session.commit()
            return True, "留言成功"
        except Exception as e:
            self.session.rollback()
            return False, f"留言失败: {str(e)}"

    def get_comments(self, limit=5, offset=0):
        try:
            comments = (
                self.session.query(Comment)
                .order_by(Comment.timestamp.desc())
                .limit(limit)
                .offset(offset)
                .all()
            )
            return comments
        except Exception:
            return []

    def get_comments_count(self):
        try:
            count = self.session.query(Comment).count()
            return count
        except Exception:
            return 0

    def close(self):
        self.session.close()
