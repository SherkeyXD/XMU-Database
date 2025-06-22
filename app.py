from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from database import DatabaseManager
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # 在生产环境中使用随机密钥

# 初始化数据库
db = DatabaseManager()

def is_valid_input(string):
    """验证输入是否为字母数字组合"""
    if len(string) > 0:
        return string.isalnum()
    return False

@app.route('/')
def index():
    """首页 - 博客和留言板"""
    return render_template('index.html')

@app.route('/login')
def login_page():
    """登录页面"""
    return render_template('login.html')

@app.route('/api/login', methods=['POST'])
def api_login():
    """用户登录API"""
    data = request.get_json()
    useid = data.get('useid', '').strip()
    password = data.get('password', '').strip()
    
    if not useid or not password:
        return jsonify({'success': False, 'message': '用户名和密码不能为空'})
    
    success, user = db.login_user(useid, password)
    if success:
        session['user_id'] = user.useid
        session['user_sno'] = user.sno
        session['user_type'] = user.type
        return jsonify({'success': True, 'user_type': user.type})
    else:
        return jsonify({'success': False, 'message': '用户名或密码错误'})

@app.route('/api/register', methods=['POST'])
def api_register():
    """用户注册API"""
    data = request.get_json()
    useid = data.get('useid', '').strip()
    password = data.get('password', '').strip()
    sno = data.get('sno', '').strip()
    
    if not all([useid, password, sno]):
        return jsonify({'success': False, 'message': '所有字段都不能为空'})
    
    if not all([is_valid_input(useid), is_valid_input(password), is_valid_input(sno)]):
        return jsonify({'success': False, 'message': '输入格式不正确，只允许字母和数字'})
    
    success, message = db.register_user(useid, password, sno)
    return jsonify({'success': success, 'message': message})

@app.route('/dashboard')
def dashboard():
    """用户控制台"""
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    
    user_type = session.get('user_type', 0)
    if user_type == 0:
        return render_template('student.html')
    else:
        return render_template('teacher.html')

@app.route('/api/student/grades')
def api_student_grades():
    """获取学生成绩API"""
    if 'user_id' not in session or session.get('user_type') != 0:
        return jsonify({'success': False, 'message': '权限不足'})
    
    sno = session.get('user_sno')
    grades = db.get_student_grades(sno)
    
    grades_data = []
    for grade in grades:
        grades_data.append({
            'sno': grade.sno,
            'sname': grade.sname,
            'smajor': grade.smajor,
            'cname': grade.cname,
            'igrade': grade.igrade
        })
    
    return jsonify({'success': True, 'grades': grades_data})

@app.route('/api/teacher/students')
def api_teacher_students():
    """获取教师所教课程的学生列表"""
    if 'user_id' not in session or session.get('user_type') != 1:
        return jsonify({'success': False, 'message': '权限不足'})
    
    course_name = request.args.get('course_name')
    if not course_name:
        return jsonify({'success': False, 'message': '请提供课程名称'})
    
    # 验证教师是否教授该课程
    sno = session.get('user_sno')
    teacher = db.get_teacher_info(sno)
    if not teacher or teacher.cname != course_name:
        return jsonify({'success': False, 'message': '您未教授该课程'})
    
    students = db.get_students_by_course(course_name)
    students_data = []
    for student in students:
        students_data.append({
            'sno': student.sno,
            'sname': student.sname,
            'smajor': student.smajor,
            'cname': student.cname,
            'igrade': student.igrade
        })
    
    return jsonify({'success': True, 'students': students_data})

@app.route('/api/teacher/grade', methods=['POST'])
def api_update_grade():
    """更新学生成绩API"""
    if 'user_id' not in session or session.get('user_type') != 1:
        return jsonify({'success': False, 'message': '权限不足'})
    
    data = request.get_json()
    student_sno = data.get('sno')
    course_name = data.get('course_name')
    grade = data.get('grade')
    
    if not all([student_sno, course_name, grade is not None]):
        return jsonify({'success': False, 'message': '参数不完整'})
    
    try:
        grade = int(grade)
        if grade < 0 or grade > 100:
            return jsonify({'success': False, 'message': '成绩必须在0-100之间'})
    except ValueError:
        return jsonify({'success': False, 'message': '成绩必须是数字'})
    
    # 验证教师权限
    teacher_sno = session.get('user_sno')
    teacher = db.get_teacher_info(teacher_sno)
    if not teacher or teacher.cname != course_name:
        return jsonify({'success': False, 'message': '您未教授该课程'})
    
    success, message = db.update_student_grade(student_sno, course_name, grade)
    return jsonify({'success': success, 'message': message})

@app.route('/api/change_password', methods=['POST'])
def api_change_password():
    """修改密码API"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '请先登录'})
    
    data = request.get_json()
    old_password = data.get('old_password', '').strip()
    new_password = data.get('new_password', '').strip()
    
    if not all([old_password, new_password]):
        return jsonify({'success': False, 'message': '密码不能为空'})
    
    if not is_valid_input(new_password):
        return jsonify({'success': False, 'message': '新密码格式不正确'})
    
    if old_password == new_password:
        return jsonify({'success': False, 'message': '新密码不能与原密码相同'})
    
    sno = session.get('user_sno')
    success, message = db.change_password(sno, old_password, new_password)
    return jsonify({'success': success, 'message': message})

@app.route('/api/comments', methods=['GET', 'POST'])
def api_comments():
    """留言API"""
    if request.method == 'POST':
        # 简单的频率限制
        last_comment_time = session.get('last_comment_time')
        if last_comment_time:
            last_time = datetime.fromisoformat(last_comment_time)
            if datetime.now() - last_time < timedelta(seconds=10):
                return jsonify({'error': '评论提交过于频繁'}), 429
        
        data = request.get_json()
        name = data.get('name', '').strip()
        content = data.get('content', '').strip()
        
        if not all([name, content]):
            return jsonify({'error': '姓名和内容不能为空'}), 400
        
        if len(name) > 50 or len(content) > 500:
            return jsonify({'error': '内容过长'}), 400
        
        success, message = db.add_comment(name, content)
        if success:
            session['last_comment_time'] = datetime.now().isoformat()
            return jsonify({'success': True})
        else:
            return jsonify({'error': message}), 500
    
    else:  # GET
        limit = int(request.args.get('limit', 5))
        offset = int(request.args.get('offset', 0))
        
        comments = db.get_comments(limit, offset)
        comments_data = []
        for comment in comments:
            comments_data.append({
                'name': comment.name,
                'content': comment.content,
                'timestamp': comment.timestamp.strftime('%Y-%m-%d %H:%M:%S')
            })
        
        return jsonify({'comments': comments_data})

@app.route('/api/comments/count')
def api_comments_count():
    """获取留言总数API"""
    count = db.get_comments_count()
    return jsonify({'total': count})

@app.route('/logout')
def logout():
    """退出登录"""
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)