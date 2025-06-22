from sqlalchemy import create_engine, Column, String, Integer, ForeignKey, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime
import hashlib

Base = declarative_base()


class SystemUser(Base):
    __tablename__ = "systemusers"

    useid = Column(String(20), primary_key=True)
    usepass = Column(String(64), nullable=False)  # 存储哈希密码
    sno = Column(String(20), nullable=False)
    type = Column(Integer, nullable=False)  # 0: 学生, 1: 教师


class Student(Base):
    __tablename__ = "students"

    sno = Column(String(20), primary_key=True)
    sname = Column(String(20), nullable=False)
    smajor = Column(String(20), nullable=False)
    cname = Column(String(20), nullable=False)
    igrade = Column(Integer, nullable=True)


class Teacher(Base):
    __tablename__ = "teachers"

    sno = Column(String(20), primary_key=True)
    sname = Column(String(20), nullable=False)
    cname = Column(String(20), nullable=False)


class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False)
    content = Column(String(500), nullable=False)
    timestamp = Column(DateTime, default=datetime.now)


class DatabaseManager:
    def __init__(
        self,
        database_url=r"sqlite:///gradesystem.db",
    ):
        self.engine = create_engine(database_url)
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    def hash_password(self, password):
        """密码哈希"""
        return hashlib.sha256(password.encode()).hexdigest()

    def verify_password(self, password, hashed):
        """验证密码"""
        return self.hash_password(password) == hashed

    # 用户相关操作
    def register_user(self, useid, password, sno):
        """注册新用户（学生）"""
        try:
            # 检查用户是否已存在
            existing_user = (
                self.session.query(SystemUser).filter_by(useid=useid).first()
            )
            if existing_user:
                return False, "账号已存在"

            existing_sno = self.session.query(SystemUser).filter_by(sno=sno).first()
            if existing_sno:
                return False, "学号已注册"

            # 创建新用户
            new_user = SystemUser(
                useid=useid,
                usepass=self.hash_password(password),
                sno=sno,
                type=0,  # 学生
            )
            self.session.add(new_user)
            self.session.commit()
            return True, "注册成功"
        except Exception as e:
            self.session.rollback()
            return False, f"注册失败: {str(e)}"

    def login_user(self, useid, password):
        """用户登录"""
        try:
            user = self.session.query(SystemUser).filter_by(useid=useid).first()
            if user and self.verify_password(password, user.usepass):
                return True, user
            return False, None
        except Exception as e:
            return False, None

    def change_password(self, sno, old_password, new_password):
        """修改密码"""
        try:
            user = self.session.query(SystemUser).filter_by(sno=sno).first()
            if user and self.verify_password(old_password, user.usepass):
                user.usepass = self.hash_password(new_password)
                self.session.commit()
                return True, "密码修改成功"
            return False, "原密码错误"
        except Exception as e:
            self.session.rollback()
            return False, f"修改失败: {str(e)}"

    # 学生相关操作
    def get_student_info(self, sno):
        """获取学生信息"""
        try:
            student = self.session.query(Student).filter_by(sno=sno).first()
            return student
        except Exception as e:
            return None

    def get_student_grades(self, sno):
        """获取学生成绩"""
        try:
            grades = self.session.query(Student).filter_by(sno=sno).all()
            return grades
        except Exception as e:
            return []

    # 教师相关操作
    def get_teacher_info(self, sno):
        """获取教师信息"""
        try:
            teacher = self.session.query(Teacher).filter_by(sno=sno).first()
            return teacher
        except Exception as e:
            return None

    def get_students_by_course(self, course_name):
        """根据课程获取学生列表"""
        try:
            students = self.session.query(Student).filter_by(cname=course_name).all()
            return students
        except Exception as e:
            return []

    def update_student_grade(self, sno, course_name, grade):
        """更新学生成绩"""
        try:
            student = (
                self.session.query(Student)
                .filter(Student.sno == sno, Student.cname == course_name)
                .first()
            )

            if student:
                student.igrade = grade
                self.session.commit()
                return True, "成绩更新成功"
            return False, "未找到该学生课程记录"
        except Exception as e:
            self.session.rollback()
            return False, f"更新失败: {str(e)}"

    def get_student_by_course(self, sno, course_name):
        """根据学号和课程获取学生信息"""
        try:
            student = (
                self.session.query(Student)
                .filter(Student.sno == sno, Student.cname == course_name)
                .first()
            )
            return student
        except Exception as e:
            return None

    # 留言相关操作
    def add_comment(self, name, content):
        """添加留言"""
        try:
            comment = Comment(name=name, content=content)
            self.session.add(comment)
            self.session.commit()
            return True, "留言成功"
        except Exception as e:
            self.session.rollback()
            return False, f"留言失败: {str(e)}"

    def get_comments(self, limit=5, offset=0):
        """获取留言列表"""
        try:
            comments = (
                self.session.query(Comment)
                .order_by(Comment.timestamp.desc())
                .limit(limit)
                .offset(offset)
                .all()
            )
            return comments
        except Exception as e:
            return []

    def get_comments_count(self):
        """获取留言总数"""
        try:
            count = self.session.query(Comment).count()
            return count
        except Exception as e:
            return 0

    def close(self):
        """关闭数据库连接"""
        self.session.close()
