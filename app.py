from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from database import DatabaseManager, Course, Grade, Student
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = "your-secret-key-here"  # 在生产环境中使用随机密钥

# 初始化数据库
db = DatabaseManager()


def is_valid_input(string):
    """验证输入是否为字母数字组合"""
    if len(string) > 0:
        return string.isalnum()
    return False


@app.route("/")
def index():
    """首页 - 博客和留言板"""
    return render_template("index.html")


@app.route("/login")
def login_page():
    """登录页面"""
    return render_template("login.html")


@app.route("/api/login", methods=["POST"])
def api_login():
    """用户登录API"""
    data = request.get_json()
    user_type = data.get("user_type")  # 'admin', 'teacher', 'student'
    user_id = data.get("user_id", "").strip()
    password = data.get("password", "").strip()
    if not user_id or not password:
        return jsonify({"success": False, "message": "账号和密码不能为空"})
    if user_type == "admin":
        success, user = db.admin_login(user_id, password)
        if success:
            session["user_type"] = "admin"
            session["user_id"] = user.ano
            return jsonify({"success": True, "user_type": "admin"})
    elif user_type == "teacher":
        success, user = db.teacher_login(user_id, password)
        if success:
            session["user_type"] = "teacher"
            session["user_id"] = user.tno
            return jsonify({"success": True, "user_type": "teacher"})
    elif user_type == "student":
        success, user = db.student_login(user_id, password)
        if success:
            session["user_type"] = "student"
            session["user_id"] = user.sno
            return jsonify({"success": True, "user_type": "student"})
    return jsonify({"success": False, "message": "账号或密码错误"})


@app.route("/dashboard")
def dashboard():
    """用户控制台"""
    if "user_id" not in session:
        return redirect(url_for("login_page"))

    user_type = session.get("user_type")
    if user_type == "admin":
        return render_template("admin.html")
    elif user_type == "teacher":
        return render_template("teacher.html")
    else:
        return render_template("student.html")


@app.route("/api/student/courses", methods=["GET"])
def student_get_courses():
    """查询学生已修课程及学分"""
    if "user_id" not in session or session.get("user_type") != "student":
        return jsonify({"success": False, "message": "权限不足"})

    sno = session.get("user_id")  # 学生学号

    # Get all courses and the corresponding grades for this student
    courses = (
        db.session.query(
            Course.cno, Course.cname, Course.credit, Grade.grade, Course.term
        )
        .join(Grade, Grade.cno == Course.cno)
        .filter(Grade.sno == sno)
        .all()
    )

    courses_data = []
    for course in courses:
        courses_data.append(
            {
                "cno": course.cno,
                "cname": course.cname,
                "credit": course.credit,
                "grade": course.grade,  # 学生成绩
                "term": course.term,  # 学期
            }
        )

    return jsonify({"success": True, "courses": courses_data})


@app.route("/api/teacher/students")
def api_teacher_students():
    """获取教师所教课程的学生列表"""
    if "user_id" not in session or session.get("user_type") != "teacher":
        return jsonify({"success": False, "message": "权限不足"})

    course_name = request.args.get("course_name")
    if not course_name:
        return jsonify({"success": False, "message": "请提供课程名称"})

    # 验证教师是否教授该课程
    sno = session.get("user_id")
    teacher = db.get_teacher_info(sno)
    if not teacher or teacher.cname != course_name:
        return jsonify({"success": False, "message": "您未教授该课程"})

    students = db.get_students_by_course(course_name)
    students_data = []
    for student in students:
        students_data.append(
            {
                "sno": student.sno,
                "sname": student.sname,
                "smajor": student.smajor,
                "cname": student.cname,
                "igrade": student.igrade,
            }
        )

    return jsonify({"success": True, "students": students_data})


@app.route("/api/teacher/add_grade", methods=["POST"])
def teacher_add_grade():
    if "user_id" not in session or session.get("user_type") != "teacher":
        return jsonify({"success": False, "message": "权限不足"})
    data = request.get_json()
    student_sno = data.get("student_sno")
    course_no = data.get("course_no")
    term = data.get("term")
    grade = data.get("grade")
    if not all([student_sno, course_no, term, grade is not None]):
        return jsonify({"success": False, "message": "参数不完整"})
    try:
        grade = int(grade)
        if grade < 0 or grade > 100:
            return jsonify({"success": False, "message": "成绩必须在0-100之间"})
    except ValueError:
        return jsonify({"success": False, "message": "成绩必须是数字"})
    session.get("user_id")
    # 可加权限校验，略
    success, message = db.add_grade(student_sno, course_no, term, grade)
    return jsonify({"success": success, "message": message})


@app.route("/api/teacher/update_grade", methods=["POST"])
def teacher_update_grade():
    if "user_id" not in session or session.get("user_type") != "teacher":
        return jsonify({"success": False, "message": "权限不足"})
    data = request.get_json()
    grade_id = data.get("grade_id")
    grade = data.get("grade")
    if not all([grade_id, grade is not None]):
        return jsonify({"success": False, "message": "参数不完整"})
    try:
        grade = int(grade)
        if grade < 0 or grade > 100:
            return jsonify({"success": False, "message": "成绩必须在0-100之间"})
    except ValueError:
        return jsonify({"success": False, "message": "成绩必须是数字"})
    success, message = db.update_grade(grade_id, grade)
    return jsonify({"success": success, "message": message})


@app.route("/api/change_password", methods=["POST"])
def api_change_password():
    """修改密码API"""
    if "user_id" not in session:
        return jsonify({"success": False, "message": "请先登录"})

    data = request.get_json()
    old_password = data.get("old_password", "").strip()
    new_password = data.get("new_password", "").strip()

    if not all([old_password, new_password]):
        return jsonify({"success": False, "message": "密码不能为空"})

    if not is_valid_input(new_password):
        return jsonify({"success": False, "message": "新密码格式不正确"})

    if old_password == new_password:
        return jsonify({"success": False, "message": "新密码不能与原密码相同"})

    sno = session.get("user_id")
    success, message = db.change_password(sno, old_password, new_password)
    return jsonify({"success": success, "message": message})


@app.route("/api/comments", methods=["GET", "POST"])
def api_comments():
    """留言API"""
    if request.method == "POST":
        # 简单的频率限制
        last_comment_time = session.get("last_comment_time")
        if last_comment_time:
            last_time = datetime.fromisoformat(last_comment_time)
            if datetime.now() - last_time < timedelta(seconds=10):
                return jsonify({"error": "评论提交过于频繁"}), 429

        data = request.get_json()
        name = data.get("name", "").strip()
        content = data.get("content", "").strip()

        if not all([name, content]):
            return jsonify({"error": "姓名和内容不能为空"}), 400

        if len(name) > 50 or len(content) > 500:
            return jsonify({"error": "内容过长"}), 400

        success, message = db.add_comment(name, content)
        if success:
            session["last_comment_time"] = datetime.now().isoformat()
            return jsonify({"success": True})
        else:
            return jsonify({"error": message}), 500

    else:  # GET
        limit = int(request.args.get("limit", 5))
        offset = int(request.args.get("offset", 0))

        comments = db.get_comments(limit, offset)
        comments_data = []
        for comment in comments:
            comments_data.append(
                {
                    "name": comment.name,
                    "content": comment.content,
                    "timestamp": comment.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                }
            )

        return jsonify({"comments": comments_data})


@app.route("/api/comments/count")
def api_comments_count():
    """获取留言总数API"""
    count = db.get_comments_count()
    return jsonify({"total": count})


@app.route("/logout")
def logout():
    """退出登录"""
    session.clear()
    return redirect(url_for("index"))


# ---------------- 管理员相关API ----------------
@app.route("/api/admin/add_student", methods=["POST"])
def admin_add_student():
    if session.get("user_type") != "admin":
        return jsonify({"success": False, "message": "无权限"})
    data = request.get_json()
    sno = data.get("sno")
    sname = data.get("sname")
    smajor = data.get("smajor")
    sclass = data.get("sclass")
    sex = data.get("sex")
    birthday = data.get("birthday")
    # 不传password，后端自动生成
    success, msg = db.add_student(sno, sname, smajor, sclass, sex, birthday)
    return jsonify({"success": success, "message": msg})


@app.route("/api/admin/update_student", methods=["POST"])
def admin_update_student():
    if session.get("user_type") != "admin":
        return jsonify({"success": False, "message": "无权限"})
    data = request.get_json()
    sno = data.get("sno")
    update_fields = {k: v for k, v in data.items() if k != "sno"}
    success, msg = db.update_student(sno, **update_fields)
    return jsonify({"success": success, "message": msg})


@app.route("/api/admin/delete_student", methods=["POST"])
def admin_delete_student():
    if session.get("user_type") != "admin":
        return jsonify({"success": False, "message": "无权限"})
    data = request.get_json()
    sno = data.get("sno")
    success, msg = db.delete_student(sno)
    return jsonify({"success": success, "message": msg})


@app.route("/api/admin/get_students")
def admin_get_students():
    if session.get("user_type") != "admin":
        return jsonify({"success": False, "message": "无权限"})
    students = db.get_all_students()
    return jsonify(
        {
            "success": True,
            "students": [
                {
                    "sno": s.sno,
                    "sname": s.sname,
                    "smajor": s.smajor,
                    "sclass": s.sclass,
                    "sex": s.sex,
                    "birthday": s.birthday,
                }
                for s in students
            ],
        }
    )


@app.route("/api/admin/add_teacher", methods=["POST"])
def admin_add_teacher():
    if session.get("user_type") != "admin":
        return jsonify({"success": False, "message": "无权限"})
    data = request.get_json()
    tno = data.get("tno")
    tname = data.get("tname")
    tdept = data.get("tdept")
    # 不传password，后端自动生成
    success, msg = db.add_teacher(tno, tname, tdept)
    return jsonify({"success": success, "message": msg})


@app.route("/api/admin/update_teacher", methods=["POST"])
def admin_update_teacher():
    if session.get("user_type") != "admin":
        return jsonify({"success": False, "message": "无权限"})
    data = request.get_json()
    tno = data.get("tno")
    update_fields = {k: v for k, v in data.items() if k != "tno"}
    success, msg = db.update_teacher(tno, **update_fields)
    return jsonify({"success": success, "message": msg})


@app.route("/api/admin/delete_teacher", methods=["POST"])
def admin_delete_teacher():
    if session.get("user_type") != "admin":
        return jsonify({"success": False, "message": "无权限"})
    data = request.get_json()
    tno = data.get("tno")
    success, msg = db.delete_teacher(tno)
    return jsonify({"success": success, "message": msg})


@app.route("/api/admin/get_teachers")
def admin_get_teachers():
    if session.get("user_type") != "admin":
        return jsonify({"success": False, "message": "无权限"})
    teachers = db.get_all_teachers()
    return jsonify(
        {
            "success": True,
            "teachers": [
                {"tno": t.tno, "tname": t.tname, "tdept": t.tdept} for t in teachers
            ],
        }
    )


@app.route("/api/admin/add_course", methods=["POST"])
def admin_add_course():
    if session.get("user_type") != "admin":
        return jsonify({"success": False, "message": "无权限"})
    data = request.get_json()
    cno = data.get("cno")
    cname = data.get("cname")
    credit = data.get("credit")
    tno = data.get("tno")
    term = data.get("term")
    success, msg = db.add_course(cno, cname, credit, tno, term)
    return jsonify({"success": success, "message": msg})


@app.route("/api/admin/update_course", methods=["POST"])
def admin_update_course():
    if session.get("user_type") != "admin":
        return jsonify({"success": False, "message": "无权限"})
    data = request.get_json()
    cno = data.get("cno")
    update_fields = {k: v for k, v in data.items() if k != "cno"}
    success, msg = db.update_course(cno, **update_fields)
    return jsonify({"success": success, "message": msg})


@app.route("/api/admin/delete_course", methods=["POST"])
def admin_delete_course():
    if session.get("user_type") != "admin":
        return jsonify({"success": False, "message": "无权限"})
    data = request.get_json()
    cno = data.get("cno")
    success, msg = db.delete_course(cno)
    return jsonify({"success": success, "message": msg})


@app.route("/api/admin/get_courses")
def admin_get_courses():
    if session.get("user_type") != "admin":
        return jsonify({"success": False, "message": "无权限"})
    courses = db.get_all_courses()
    return jsonify(
        {
            "success": True,
            "courses": [
                {
                    "cno": c.cno,
                    "cname": c.cname,
                    "credit": c.credit,
                    "tno": c.tno,
                    "term": c.term,
                }
                for c in courses
            ],
        }
    )


@app.route("/api/admin/get_grades")
def admin_get_grades():
    if session.get("user_type") != "admin":
        return jsonify({"success": False, "message": "无权限"})
    grades = db.get_all_grades()
    return jsonify(
        {
            "success": True,
            "grades": [
                {
                    "id": g.id,
                    "sno": g.sno,
                    "cno": g.cno,
                    "term": g.term,
                    "grade": g.grade,
                }
                for g in grades
            ],
        }
    )


@app.route("/api/admin/change_password", methods=["POST"])
def admin_change_password():
    if session.get("user_type") != "admin":
        return jsonify({"success": False, "message": "无权限"})
    data = request.get_json()
    old_password = data.get("old_password")
    new_password = data.get("new_password")
    admin = db.get_admin(session["user_id"])
    if not db.verify_password(old_password, admin.password):
        return jsonify({"success": False, "message": "原密码错误"})
    success, msg = db.update_admin(admin.ano, password=new_password)
    return jsonify({"success": success, "message": msg})


# ---------------- 管理员账号管理API ----------------
@app.route("/api/admin/add_admin", methods=["POST"])
def admin_add_admin():
    if session.get("user_type") != "admin":
        return jsonify({"success": False, "message": "无权限"})
    data = request.get_json()
    ano = data.get("ano")
    aname = data.get("aname")
    password = data.get("password", f"{ano}/123456")
    success, msg = db.add_admin(ano, aname, password)
    return jsonify({"success": success, "message": msg})


@app.route("/api/admin/update_admin", methods=["POST"])
def admin_update_admin():
    if session.get("user_type") != "admin":
        return jsonify({"success": False, "message": "无权限"})
    data = request.get_json()
    ano = data.get("ano")
    aname = data.get("aname")
    password = data.get("password")  # 可选
    success, msg = db.update_admin(ano, aname, password)
    return jsonify({"success": success, "message": msg})


@app.route("/api/admin/delete_admin", methods=["POST"])
def admin_delete_admin():
    if session.get("user_type") != "admin":
        return jsonify({"success": False, "message": "无权限"})
    data = request.get_json()
    ano = data.get("ano")
    success, msg = db.delete_admin(ano)
    return jsonify({"success": success, "message": msg})


@app.route("/api/admin/get_admins")
def admin_get_admins():
    if session.get("user_type") != "admin":
        return jsonify({"success": False, "message": "无权限"})
    admins = db.get_all_admins()
    return jsonify(
        {"success": True, "admins": [{"ano": a.ano, "aname": a.aname} for a in admins]}
    )


# ---------------- 教师相关API ----------------
@app.route("/api/teacher/enter_grade", methods=["POST"])
def teacher_enter_grade():
    """教师录入成绩"""
    if "user_id" not in session or session.get("user_type") != "teacher":
        return jsonify({"success": False, "message": "权限不足"})

    data = request.get_json()
    student_sno = data.get("sno")
    course_name = data.get("course_name")
    grade = data.get("grade")

    if not all([student_sno, course_name, grade is not None]):
        return jsonify({"success": False, "message": "参数不完整"})

    try:
        grade = int(grade)
        if grade < 0 or grade > 100:
            return jsonify({"success": False, "message": "成绩必须在0-100之间"})
    except ValueError:
        return jsonify({"success": False, "message": "成绩必须是数字"})

    # 验证教师权限
    teacher_sno = session.get("user_id")
    teacher = db.get_teacher_info(teacher_sno)
    if not teacher or teacher.cname != course_name:
        return jsonify({"success": False, "message": "您未教授该课程"})

    success, message = db.update_student_grade(student_sno, course_name, grade)
    return jsonify({"success": success, "message": message})


@app.route("/api/teacher/get_info", methods=["GET"])
def teacher_get_info():
    """查询教师个人信息"""
    if "user_id" not in session or session.get("user_type") != "teacher":
        return jsonify({"success": False, "message": "权限不足"})

    teacher_sno = session.get("user_id")
    teacher_info = db.get_teacher(teacher_sno)

    if not teacher_info:
        return jsonify({"success": False, "message": "教师不存在"})

    teacher_data = {
        "tno": teacher_info.tno,  # 工号
        "tname": teacher_info.tname,  # 姓名
        "tdept": teacher_info.tdept,  # 院系
    }

    return jsonify({"success": True, "teacher": teacher_data})


@app.route("/api/teacher/update_info", methods=["POST"])
def teacher_update_info():
    """查询并修改教师个人信息"""
    if "user_id" not in session or session.get("user_type") != "teacher":
        return jsonify({"success": False, "message": "权限不足"})

    data = request.get_json()
    teacher_sno = session.get("user_id")
    teacher_info = db.get_teacher(teacher_sno)

    if not teacher_info:
        return jsonify({"success": False, "message": "教师不存在"})

    # 返回教师工号（tno）、姓名（tname）和院系（tdept）
    teacher_data = {
        "tno": teacher_info.tno,
        "tname": teacher_info.tname,
        "tdept": teacher_info.tdept,
    }

    # 更新教师信息（包括修改密码）
    updated_fields = {
        k: v for k, v in data.items() if k in ["tname", "tdept", "password"]
    }
    if "password" in updated_fields:
        updated_fields["password"] = db.hash_password(updated_fields["password"])

    success, message = db.update_teacher(teacher_sno, **updated_fields)

    if success:
        return jsonify(
            {"success": True, "message": "信息更新成功", "teacher": teacher_data}
        )
    else:
        return jsonify({"success": False, "message": message})


@app.route("/api/teacher/change_password", methods=["POST"])
def teacher_change_password():
    if session.get("user_type") != "teacher":
        return jsonify({"success": False, "message": "无权限"})
    data = request.get_json()
    old_password = data.get("old_password")
    new_password = data.get("new_password")
    teacher = db.get_teacher(session["user_id"])
    if not db.verify_password(old_password, teacher.password):
        return jsonify({"success": False, "message": "原密码错误"})
    success, msg = db.update_teacher(teacher.tno, password=new_password)
    return jsonify({"success": success, "message": msg})


@app.route("/api/teacher/grades", methods=["GET"])
def teacher_get_grades():
    """查询教师已录入的成绩"""
    if "user_id" not in session or session.get("user_type") != "teacher":
        return jsonify({"success": False, "message": "权限不足"})

    course_name = request.args.get("course_name")  # 课程名称
    term = request.args.get("term")  # 学期
    student_sno = request.args.get("student_sno")  # 学生学号

    teacher_sno = session.get("user_id")
    db.get_teacher(teacher_sno)

    # 根据课程名称获取课程编号
    course = db.session.query(Course).filter_by(cname=course_name).first()

    if not course:
        return jsonify({"success": False, "message": "课程不存在"})

    # 检查教师是否教授该课程
    if course.tno != teacher_sno:
        return jsonify({"success": False, "message": "您未教授该课程"})

    # 查询成绩并连接学生表以获取学生姓名
    grades = (
        db.session.query(Grade, Student.sname)
        .join(Student, Grade.sno == Student.sno)
        .filter(Grade.cno == course.cno)
    )

    if term:
        grades = grades.filter(Grade.term == term)
    if student_sno:
        grades = grades.filter(Grade.sno == student_sno)

    grades = grades.all()

    if not grades:
        return jsonify({"success": False, "message": "没有成绩记录"})

    grades_data = []
    for grade, sname in grades:
        grades_data.append(
            {
                "sno": grade.sno,  # 学生学号
                "sname": sname,  # 学生姓名
                "course_name": grade.course.cname,  # 课程名称
                "grade": grade.grade,  # 成绩
                "term": grade.term,  # 学期
            }
        )

    return jsonify({"success": True, "grades": grades_data})


@app.route("/api/teacher/add_course", methods=["POST"])
def teacher_add_course():
    if "user_id" not in session or session.get("user_type") != "teacher":
        return jsonify({"success": False, "message": "权限不足"})
    data = request.get_json()
    cno = data.get("cno")
    cname = data.get("cname")
    credit = data.get("credit")
    term = data.get("term")
    tno = session.get("user_id")
    # 只允许添加自己名下的课程
    success, msg = db.add_course(cno, cname, credit, tno, term)
    return jsonify({"success": success, "message": msg})


# ---------------- 学生相关API ----------------
@app.route("/api/student/get_info", methods=["GET"])
def student_get_info():
    """获取学生信息API"""
    if "user_id" not in session or session.get("user_type") != "student":
        return jsonify({"success": False, "message": "权限不足"})

    sno = session.get("user_id")
    student = db.get_student(sno)

    if not student:
        return jsonify({"success": False, "message": "学生不存在"})

    student_data = {
        "sno": student.sno,
        "sname": student.sname,
        "smajor": student.smajor,
        "sclass": student.sclass,
        "sex": student.sex,
        "birthday": student.birthday,
    }

    return jsonify({"success": True, "student": student_data})


@app.route("/api/student/update_info", methods=["POST"])
def student_update_info():
    """查询并修改学生个人信息"""
    if "user_id" not in session or session.get("user_type") != "student":
        return jsonify({"success": False, "message": "权限不足"})

    data = request.get_json()
    student_sno = session.get("user_id")
    student_info = db.get_student(student_sno)

    if not student_info:
        return jsonify({"success": False, "message": "学生不存在"})

    # 更新学生信息（包括修改密码）
    updated_fields = {
        k: v
        for k, v in data.items()
        if k in ["sname", "smajor", "sclass", "sex", "birthday", "password"]
    }
    if "password" in updated_fields:
        updated_fields["password"] = db.hash_password(updated_fields["password"])

    success, message = db.update_student(student_sno, **updated_fields)
    return jsonify({"success": success, "message": message})


@app.route("/api/student/grades", methods=["GET"])
def student_get_grades():
    """查询学生的成绩"""
    if "user_id" not in session or session.get("user_type") != "student":
        return jsonify({"success": False, "message": "权限不足"})

    sno = session.get("user_id")  # 学生学号
    course_no = request.args.get("course_no")
    term = request.args.get("term")

    # 查询该学生的成绩，并连接课程表
    grades_query = (
        db.session.query(Grade, Course)
        .join(Course, Grade.cno == Course.cno)
        .filter(Grade.sno == sno)
    )

    if course_no:
        grades_query = grades_query.filter(Course.cno == course_no)
    if term:
        grades_query = grades_query.filter(Grade.term == term)

    grades = grades_query.all()

    grades_data = []
    for grade, course in grades:
        grades_data.append(
            {
                "sno": grade.sno,  # 学号
                "cname": course.cname,  # 课程名称
                "cno": course.cno,  # 课程编号
                "term": grade.term,  # 学期
                "grade": grade.grade,  # 成绩
            }
        )

    return jsonify({"success": True, "grades": grades_data})


@app.route("/api/student/change_password", methods=["POST"])
def student_change_password():
    if session.get("user_type") != "student":
        return jsonify({"success": False, "message": "无权限"})
    data = request.get_json()
    old_password = data.get("old_password")
    new_password = data.get("new_password")
    student = db.get_student(session["user_id"])
    if not db.verify_password(old_password, student.password):
        return jsonify({"success": False, "message": "原密码错误"})
    success, msg = db.update_student(student.sno, password=new_password)
    return jsonify({"success": success, "message": msg})


if __name__ == "__main__":
    app.run(debug=True)
