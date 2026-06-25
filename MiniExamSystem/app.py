import random
import string
import datetime
import json
import dashscope
from dashscope import Generation
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, TextAreaField, IntegerField, DateTimeField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length, Email, NumberRange
from sqlalchemy import func

# ====================== 全局配置 ======================
app = Flask(__name__)
# 表单加密密钥
app.config['SECRET_KEY'] = 'exam-system-secret-key-2026-mini'
# SQLite数据库文件
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///exam.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# 通义千问API密钥（需求固定key）
dashscope.api_key = "sk-22ff2a82f9e8447591468a017292d88c"
# JSON解析过滤器，模板内 | loadjson 使用
@app.template_filter('loadjson')
def load_json_filter(s):
    try:
        return json.loads(s)
    except:
        return []
# ====================== 工具函数 ======================
# 1. 生成老师6位数字专属身份码
def create_teacher_id_code():
    return ''.join(random.choices(string.digits, k=6))

# 2. 生成6位字母+数字混合考试码
def create_exam_code():
    char_pool = string.ascii_letters + string.digits
    return ''.join(random.choices(char_pool, k=6))

# 3. 时间工具：判断时间是否过期
def is_time_expire(target_time: datetime.datetime) -> bool:
    now = datetime.datetime.now()
    return now > target_time

# 4. AI出题封装：支持单选/多选/判断/填空/解答 + 自定义主题
def ai_generate_question(q_type, count, subject, difficulty="中等"):
    """
    q_type: single(单选) / multi(多选) / judge(判断) / blank(填空) / answer(解答)
    count: 题目数量
    subject: 出题主题/知识点
    return: 结构化题目JSON字符串
    """
    prompt_map = {
        "single": f"围绕知识点「{subject}」生成{count}道{difficulty}难度单选题，输出JSON数组，每道题包含：question题干、options选项数组、answer正确答案、score分值默认2分",
        "multi": f"围绕知识点「{subject}」生成{count}道{difficulty}难度多选题，输出JSON数组，每道题包含：question题干、options选项数组、answer正确答案数组、score分值默认4分",
        "judge": f"围绕知识点「{subject}」生成{count}道{difficulty}难度判断题，输出JSON数组，每道题包含：question题干、answer布尔值true/false、score分值默认1分",
        "blank": f"围绕知识点「{subject}」生成{count}道{difficulty}难度填空题，输出JSON数组，每道题包含：question题干、answer标准答案、score分值默认3分",
        "answer": f"围绕知识点「{subject}」生成{count}道{difficulty}难度简答题，输出JSON数组，每道题包含：question题干、answer参考答案、score分值默认10分"
    }
    prompt = prompt_map[q_type] + "仅返回纯JSON，不要多余文字、解释、标题"
    response = Generation.call(
        model='qwen-turbo',
        prompt=prompt,
        result_format='json',
        stream=False
    )
    if response.status_code == 200:
        return response.output.choices[0].message.content
    else:
        return None

# ====================== 数据库模型定义（全表） ======================
# 1. 用户表：管理员/老师/学生
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(30), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(10), nullable=False)  # admin / teacher / student
    email = db.Column(db.String(50), unique=True)
    # 老师专属6位数字身份码，学生/管理员为空
    teacher_code = db.Column(db.String(6), unique=True, nullable=True)
    create_time = db.Column(db.DateTime, default=datetime.datetime.now)

    # 关联：老师关联的学生、自己的题库、自己创建的考试
    relate_students = db.relationship('TeacherStudentRelate', foreign_keys='TeacherStudentRelate.teacher_id', backref='teacher', lazy=True)
    my_questions = db.relationship('QuestionBank', backref='owner', lazy=True)
    my_exams = db.relationship('Exam', backref='creator', lazy=True)

# 2. 师生关联中间表（老师<->学生绑定/取关）
class TeacherStudentRelate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    create_time = db.Column(db.DateTime, default=datetime.datetime.now)
    # 联合唯一：同一个学生不能重复绑定同一个老师
    __table_args__ = (db.UniqueConstraint('teacher_id', 'student_id', name='unique_tea_stu'),)
    student = db.relationship('User', foreign_keys=[student_id], backref='relate_teachers')

# 3. 个人题库表（所有老师自有题目，AI出题/手动出题都存入）
class QuestionBank(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    q_type = db.Column(db.String(10), nullable=False)  # single/multi/judge/blank/answer
    question = db.Column(db.Text, nullable=False)
    options = db.Column(db.Text)  # 单选多选选项，JSON字符串存储
    answer = db.Column(db.Text, nullable=False)  # 答案JSON
    score = db.Column(db.Integer, default=2)
    is_shared = db.Column(db.Boolean, default=False)  # 是否共享到公共题库
    create_time = db.Column(db.DateTime, default=datetime.datetime.now)

# 4. 公共共享题库表（老师勾选共享后同步至此，其他老师可收藏）
class SharedQuestion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    source_q_id = db.Column(db.Integer, db.ForeignKey('question_bank.id'), nullable=False)
    source_teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    share_time = db.Column(db.DateTime, default=datetime.datetime.now)
    source_question = db.relationship('QuestionBank', backref='share_record')
    source_teacher = db.relationship('User', foreign_keys=[source_teacher_id])

# 5. 考试表（老师创建的每场考试，核心业务表）
class Exam(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    exam_name = db.Column(db.String(50), nullable=False)
    # 考试码相关
    use_exam_code = db.Column(db.Boolean, default=False)  # 是否启用6位考试码
    exam_code = db.Column(db.String(6), unique=True, nullable=True)
    code_expire_time = db.Column(db.DateTime, nullable=True)  # 考试码有效截止时间
    # 考试时间配置
    exam_start_time = db.Column(db.DateTime, nullable=False)  # 考试正式开始时间
    exam_duration = db.Column(db.Integer, nullable=False)  # 学生答题时长 单位分钟
    exam_end_time = db.Column(db.DateTime)  # 自动计算：开始时间+答题时长
    # 考试设置
    shuffle_question = db.Column(db.Boolean, default=True)  # 是否打乱题目顺序
    total_score = db.Column(db.Integer, default=100)  # 试卷总分默认100
    show_answer_immediately = db.Column(db.Boolean, default=True)  # 考完立刻显示答案分数
    is_finish = db.Column(db.Boolean, default=False)  # 整场考试是否结束
    # 试卷题目配置（JSON存储选中的题库ID、随机抽取数量）
    select_q_ids = db.Column(db.Text, nullable=False)  # 批量选中的题库题目id数组
    random_pick_num = db.Column(db.Integer, nullable=False)  # 从选中题目里随机抽多少道
    create_time = db.Column(db.DateTime, default=datetime.datetime.now)
    # 关联学生答卷
    student_records = db.relationship('ExamRecord', backref='exam', lazy=True)

# 6. 学生考试答卷/成绩记录表
class ExamRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey('exam.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    student = db.relationship('User', backref='exam_records')
    answer_content = db.Column(db.Text)  # 学生作答内容JSON
    get_score = db.Column(db.Integer, default=0)
    submit_time = db.Column(db.DateTime)
    is_submit = db.Column(db.Boolean, default=False)  # 是否提交试卷

# ====================== 数据库初始化函数 ======================
def create_db():
    with app.app_context():
        db.create_all()
        # 初始化默认管理员账号（仅首次创建库时生成）
        admin = User.query.filter_by(username="admin").first()
        if not admin:
            new_admin = User(
                username="admin",
                password="admin123",
                role="admin",
                email="admin@exam.com",
                teacher_code=None
            )
            db.session.add(new_admin)
            db.session.commit()
    print("数据库初始化完成，默认管理员账号：admin / admin123")

# ====================== 页面表单类 ======================
# 登录表单
class LoginForm(FlaskForm):
    username = StringField('账号', validators=[DataRequired(), Length(min=3, max=30)])
    password = PasswordField('密码', validators=[DataRequired(), Length(min=6)])
    submit = StringField('登录')

# 注册表单（可选老师/学生身份）
class RegisterForm(FlaskForm):
    username = StringField('账号', validators=[DataRequired(), Length(min=3, max=30)])
    password = PasswordField('密码', validators=[DataRequired(), Length(min=6)])
    email = StringField('邮箱', validators=[DataRequired()])
    role = SelectField('注册身份', choices=[('student', '学生'), ('teacher', '老师')], validators=[DataRequired()])
    submit = StringField('注册')

# AI出题表单
class AICreateQForm(FlaskForm):
    subject = StringField('出题主题/知识点', validators=[DataRequired(), Length(min=2, max=100)])
    q_type = SelectField('题目类型', choices=[
        ('single', '单选题'), ('multi', '多选题'), ('judge', '判断题'),
        ('blank', '填空题'), ('answer', '解答题')
    ])
    q_count = IntegerField('出题数量', validators=[DataRequired(), NumberRange(min=1, max=20)], default=5)
    submit = SubmitField('AI生成题目')

# 创建考试表单
class CreateExamForm(FlaskForm):
    exam_name = StringField('考试名称', validators=[DataRequired()])
    use_exam_code = BooleanField('启用6位考试码')
    code_expire_time = DateTimeField('考试码有效截止时间(启用考试码必填)', format='%Y-%m-%d %H:%M')
    exam_start_time = DateTimeField('考试正式开始时间', format='%Y-%m-%d %H:%M', validators=[DataRequired()])
    exam_duration = IntegerField('学生答题时长(分钟)', validators=[DataRequired(), NumberRange(min=10)], default=60)
    shuffle_question = BooleanField('打乱题目顺序', default=True)
    total_score = IntegerField('试卷总分', validators=[DataRequired()], default=100)
    show_answer_immediately = BooleanField('学生交卷后立刻展示分数与答案', default=True)
    random_pick_num = IntegerField('从选中题库随机抽取题目数量', validators=[DataRequired(), NumberRange(min=1)])
    # 修复：使用SubmitField生成按钮，不再是输入框
    submit = SubmitField('创建考试')

# 师生搜索表单
class SearchTeacherForm(FlaskForm):
    teacher_code = StringField('老师6位身份码', validators=[DataRequired(), Length(min=6, max=6)])
    submit = SubmitField('搜索老师')

# 考试码搜索表单
class SearchExamCodeForm(FlaskForm):
    exam_code = StringField('6位考试码', validators=[DataRequired(), Length(min=6, max=6)])
    submit = SubmitField('查找考试')

# ====================== 公共基础路由（登录/注册/登出/首页跳转） ======================
@app.route('/')
def index():
    # 根据session登录角色跳转对应首页
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    if user.role == "admin":
        return redirect(url_for('admin_index'))
    elif user.role == "teacher":
        return redirect(url_for('teacher_index'))
    else:
        return redirect(url_for('student_index'))

@app.route('/login', methods=['GET','POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.password == form.password.data:
            session['user_id'] = user.id
            session['user_role'] = user.role
            flash("登录成功")
            return redirect(url_for('index'))
        else:
            flash("账号或密码错误")
    return render_template('auth/login.html', form=form)

@app.route('/register', methods=['GET','POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        # 查重
        if User.query.filter_by(username=form.username.data).first():
            flash("账号已存在")
            return redirect(url_for('register'))
        # 老师自动生成6位身份码
        tea_code = None
        if form.role.data == "teacher":
            while True:
                code = create_teacher_id_code()
                if not User.query.filter_by(teacher_code=code).first():
                    tea_code = code
                    break
        new_user = User(
            username=form.username.data,
            password=form.password.data,
            email=form.email.data,
            role=form.role.data,
            teacher_code=tea_code
        )
        db.session.add(new_user)
        db.session.commit()
        flash("注册成功，请登录")
        return redirect(url_for('login'))
    return render_template('auth/register.html', form=form)

@app.route('/logout')
def logout():
    session.clear()
    flash("已退出登录")
    return redirect(url_for('login'))

# ====================== 管理员路由 ======================
@app.route('/admin/index')
def admin_index():
    # 权限校验
    if session.get("user_role") != "admin":
        flash("无管理员权限，请登录管理员账号")
        return redirect(url_for('login'))
    # 统计各类数据
    total_user = User.query.count()
    admin_count = User.query.filter_by(role="admin").count()
    teacher_count = User.query.filter_by(role="teacher").count()
    student_count = User.query.filter_by(role="student").count()
    exam_count = Exam.query.count()
    return render_template("admin/index.html",
                           total_user=total_user,
                           admin_count=admin_count,
                           teacher_count=teacher_count,
                           student_count=student_count,
                           exam_count=exam_count)

@app.route('/admin/user/manage')
def user_manage():
    if session.get("user_role") != "admin":
        flash("无管理员权限")
        return redirect(url_for('login'))
    user_list = User.query.all()
    return render_template("admin/user_manage.html", user_list=user_list)

@app.route('/admin/user/delete/<int:uid>')
def delete_user(uid):
    if session.get("user_role") != "admin":
        flash("无管理员权限")
        return redirect(url_for('login'))
    user = User.query.get_or_404(uid)
    # 禁止删除默认管理员
    if user.username == "admin":
        flash("默认管理员账号不允许删除")
        return redirect(url_for('user_manage'))
    # 级联删除该用户所有关联数据
    # 1. 删除师生关联
    TeacherStudentRelate.query.filter((TeacherStudentRelate.teacher_id == uid) | (TeacherStudentRelate.student_id == uid)).delete()
    # 2. 删除该用户创建的所有考试答卷
    ExamRecord.query.filter_by(student_id=uid).delete()
    # 3. 删除该老师创建的考试
    Exam.query.filter_by(creator_id=uid).delete()
    # 4. 删除题库与共享题目
    q_list = QuestionBank.query.filter_by(owner_id=uid).all()
    for q in q_list:
        SharedQuestion.query.filter_by(source_q_id=q.id).delete()
    QuestionBank.query.filter_by(owner_id=uid).delete()
    # 5. 删除用户本身
    db.session.delete(user)
    db.session.commit()
    flash("用户账号及关联数据已全部删除")
    return redirect(url_for('user_manage'))

# ====================== 教师基础路由：首页、个人中心、AI出题 ======================
@app.route('/teacher/index')
def teacher_index():
    if session.get("user_role") != "teacher":
        flash("仅教师账号可访问此页面")
        return redirect(url_for('login'))
    uid = session["user_id"]
    current_user = User.query.get(uid)
    now = datetime.datetime.now()
    # 查询所有未结束的考试
    unfinished_exams = Exam.query.filter(
        Exam.creator_id == uid,
        Exam.exam_end_time > now,
        Exam.is_finish == False
    ).all()
    return render_template("teacher/index.html", current_user=current_user, unfinished_exams=unfinished_exams)

@app.route('/teacher/profile')
def teacher_profile():
    if session.get("user_role") != "teacher":
        flash("权限不足")
        return redirect(url_for('login'))
    user = User.query.get(session["user_id"])
    return render_template("teacher/profile.html", user=user)

@app.route('/teacher/question/ai-create', methods=["GET", "POST"])
def ai_create_question():
    if session.get("user_role") != "teacher":
        flash("仅教师可使用AI出题功能")
        return redirect(url_for('login'))
    form = AICreateQForm()
    result_msg = ""
    if form.validate_on_submit():
        q_type = form.q_type.data
        count = form.q_count.data
        subject = form.subject.data
        # 调用通义千问API
        json_str = ai_generate_question(q_type, count, subject)
        if not json_str:
            flash("AI生成题目失败，请稍后重试")
            return render_template("teacher/question/ai_create.html", form=form)
        try:
            q_list = json.loads(json_str)
            owner_id = session["user_id"]
            for item in q_list:
                new_q = QuestionBank(
                    owner_id=owner_id,
                    q_type=q_type,
                    question=item["question"],
                    options=json.dumps(item.get("options", [])),
                    answer=json.dumps(item["answer"]),
                    score=item.get("score", 2)
                )
                db.session.add(new_q)
            db.session.commit()
            result_msg = f"成功生成 {len(q_list)} 道题目，已存入您的个人题库！"
        except Exception as e:
            db.session.rollback()
            flash(f"解析AI返回数据失败：{str(e)}")
    return render_template("teacher/question/ai_create.html", form=form, result_msg=result_msg)

# ====================== 教师：个人题库、共享题库、师生关联解绑 ======================
@app.route('/teacher/question/my-bank')
def my_question_bank():
    if session.get("user_role") != "teacher":
        flash("仅教师可访问题库")
        return redirect(url_for('login'))
    uid = session["user_id"]
    q_list = QuestionBank.query.filter_by(owner_id=uid).all()
    return render_template("teacher/question/my_bank.html", q_list=q_list)

# 批量共享选中题目
@app.route('/teacher/question/batch-share', methods=["POST"])
def batch_share_question():
    if session.get("user_role") != "teacher":
        flash("权限不足")
        return redirect(url_for('login'))
    q_ids_str = request.form.get("q_ids", "")
    if not q_ids_str:
        flash("未选择任何题目")
        return redirect(url_for('my_question_bank'))
    id_list = [int(i) for i in q_ids_str.split(",")]
    teacher_id = session["user_id"]
    for qid in id_list:
        q = QuestionBank.query.get(qid)
        if q and q.owner_id == teacher_id and not q.is_shared:
            q.is_shared = True
            # 写入共享题库表
            share_item = SharedQuestion(
                source_q_id=q.id,
                source_teacher_id=teacher_id
            )
            db.session.add(share_item)
    db.session.commit()
    flash(f"成功共享 {len(id_list)} 道题目到公共题库")
    return redirect(url_for('my_question_bank'))

# 公共共享题库页面
@app.route('/teacher/question/share-bank')
def share_bank():
    if session.get("user_role") != "teacher":
        flash("仅教师可查看共享题库")
        return redirect(url_for('login'))
    share_list = SharedQuestion.query.join(User, SharedQuestion.source_teacher_id == User.id).all()
    return render_template("teacher/question/share_bank.html", share_list=share_list)

# 批量把共享题目存入个人题库
@app.route('/teacher/question/batch-save-share', methods=["POST"])
def batch_save_share_q():
    if session.get("user_role") != "teacher":
        flash("权限不足")
        return redirect(url_for('share_bank'))
    share_ids_str = request.form.get("share_ids", "")
    if not share_ids_str:
        flash("未选择共享题目")
        return redirect(url_for('share_bank'))
    id_list = [int(i) for i in share_ids_str.split(",")]
    login_tea_id = session["user_id"]
    add_count = 0
    for sid in id_list:
        share_q = SharedQuestion.query.get(sid)
        if not share_q:
            continue
        src_q = share_q.source_question
        # 复制题目到当前老师题库
        new_q = QuestionBank(
            owner_id=login_tea_id,
            q_type=src_q.q_type,
            question=src_q.question,
            options=src_q.options,
            answer=src_q.answer,
            score=src_q.score,
            is_shared=False
        )
        db.session.add(new_q)
        add_count += 1
    db.session.commit()
    flash(f"成功将 {add_count} 道共享题目存入你的个人题库")
    return redirect(url_for('share_bank'))

# 查看绑定自己的学生
@app.route('/teacher/relate-student')
def relate_student_list():
    if session.get("user_role") != "teacher":
        flash("权限不足")
        return redirect(url_for('login'))
    tea_id = session["user_id"]
    rel_list = TeacherStudentRelate.query.filter_by(teacher_id=tea_id).join(User, TeacherStudentRelate.student_id == User.id).all()
    return render_template("teacher/relate_stu.html", stu_list=rel_list)

# 解绑学生
@app.route('/teacher/unbind-student/<int:rel_id>')
def unbind_student(rel_id):
    if session.get("user_role") != "teacher":
        flash("权限不足")
        return redirect(url_for('login'))
    rel = TeacherStudentRelate.query.get_or_404(rel_id)
    # 校验只能解绑自己的学生
    if rel.teacher_id != session["user_id"]:
        flash("非法操作，无法解绑他人关联关系")
        return redirect(url_for('relate_student_list'))
    db.session.delete(rel)
    db.session.commit()
    flash("已解除与该学生的关联绑定")
    return redirect(url_for('relate_student_list'))

# ====================== 教师考试模块路由 ======================
@app.route('/teacher/exam/create', methods=["GET","POST"])
def create_exam():
    if session.get("user_role") != "teacher":
        flash("仅教师可创建考试")
        return redirect(url_for('login'))
    uid = session["user_id"]
    form = CreateExamForm()
    # 加载当前老师全部题库题目供选择
    q_list = QuestionBank.query.filter_by(owner_id=uid).all()
    if form.validate_on_submit():
        # 获取选中的题库id
        select_q_ids_str = request.form.get("select_q_ids", "")
        select_q_ids = select_q_ids_str.split(",")
        # 基础参数
        exam_name = form.exam_name.data
        use_exam_code = form.use_exam_code.data
        code_expire = form.code_expire_time.data
        start_time = form.exam_start_time.data
        duration = form.exam_duration.data
        shuffle = form.shuffle_question.data
        total_score = form.total_score.data
        show_ans = form.show_answer_immediately.data
        random_pick = form.random_pick_num.data
        # 计算考试结束时间 = 开始时间 + 答题时长分钟
        exam_end = start_time + datetime.timedelta(minutes=duration)
        # 生成考试码
        exam_code = None
        if use_exam_code:
            while True:
                temp_code = create_exam_code()
                if not Exam.query.filter_by(exam_code=temp_code).first():
                    exam_code = temp_code
                    break
        # 新建考试记录
        new_exam = Exam(
            creator_id=uid,
            exam_name=exam_name,
            use_exam_code=use_exam_code,
            exam_code=exam_code,
            code_expire_time=code_expire,
            exam_start_time=start_time,
            exam_duration=duration,
            exam_end_time=exam_end,
            shuffle_question=shuffle,
            total_score=total_score,
            show_answer_immediately=show_ans,
            is_finish=False,
            select_q_ids=select_q_ids_str,
            random_pick_num=random_pick
        )
        db.session.add(new_exam)
        db.session.commit()
        flash(f"考试创建成功！考试码：{exam_code if exam_code else '未启用'}")
        return redirect(url_for('exam_list'))
    return render_template("teacher/exam/create_exam.html", form=form, q_list=q_list)

@app.route('/teacher/exam/list')
def exam_list():
    if session.get("user_role") != "teacher":
        flash("权限不足")
        return redirect(url_for('login'))
    uid = session["user_id"]
    exam_list = Exam.query.filter_by(creator_id=uid).order_by(Exam.create_time.desc()).all()
    return render_template("teacher/exam/exam_list.html", exam_list=exam_list)

@app.route('/teacher/exam/delete/<int:exam_id>')
def delete_exam(exam_id):
    if session.get("user_role") != "teacher":
        flash("权限不足")
        return redirect(url_for('login'))
    exam = Exam.query.get_or_404(exam_id)
    if exam.creator_id != session["user_id"]:
        flash("不能删除他人创建的考试")
        return redirect(url_for('exam_list'))
    if exam.is_finish:
        flash("已结束考试不允许删除")
        return redirect(url_for('exam_list'))
    # 删除所有答卷
    ExamRecord.query.filter_by(exam_id=exam_id).delete()
    db.session.delete(exam)
    db.session.commit()
    flash("考试已删除，所有答卷数据清空")
    return redirect(url_for('exam_list'))

@app.route('/teacher/exam/stat/<int:exam_id>')
def exam_stat(exam_id):
    if session.get("user_role") != "teacher":
        flash("权限不足")
        return redirect(url_for('login'))
    exam = Exam.query.get_or_404(exam_id)
    if exam.creator_id != session["user_id"]:
        flash("无权查看他人考试统计")
        return redirect(url_for('exam_list'))
    record_list = ExamRecord.query.filter_by(exam_id=exam_id).join(User, ExamRecord.student_id == User.id).all()
    return render_template("teacher/exam/exam_stat.html", exam=exam, record_list=record_list)

@app.route('/teacher/exam/edit/<int:exam_id>', methods=["GET","POST"])
def edit_exam(exam_id):
    if session.get("user_role") != "teacher":
        flash("权限不足")
        return redirect(url_for('login'))
    exam = Exam.query.get_or_404(exam_id)
    if exam.creator_id != session["user_id"] or exam.is_finish:
        flash("仅可修改自己创建的未结束考试")
        return redirect(url_for('exam_list'))
    form = CreateExamForm(obj=exam)
    # 只允许修改时间相关字段，题目、总分、抽题数量不可改
    if form.validate_on_submit():
        exam.code_expire_time = form.code_expire_time.data
        exam.exam_start_time = form.exam_start_time.data
        exam.exam_duration = form.exam_duration.data
        exam.exam_end_time = exam.exam_start_time + datetime.timedelta(minutes=exam.exam_duration)
        db.session.commit()
        flash("考试时间修改完成")
        return redirect(url_for('exam_list'))
    uid = session["user_id"]
    q_list = QuestionBank.query.filter_by(owner_id=uid).all()
    return render_template("teacher/exam/create_exam.html", form=form, q_list=q_list)

# ====================== 学生端全部业务路由 ======================
# 学生首页
@app.route('/student/index')
def student_index():
    if session.get("user_role") != "student":
        flash("仅学生账号访问")
        return redirect(url_for('login'))
    stu_id = session["user_id"]
    now = datetime.datetime.now()
    user = User.query.get(stu_id)
    # 查询所有未交卷的考试记录
    wait_exam_list = ExamRecord.query.filter_by(student_id=stu_id, is_submit=False).join(Exam).all()
    return render_template("student/index.html", user=user, wait_exam_list=wait_exam_list, now=now)

# 学生个人中心
@app.route('/student/profile')
def student_profile():
    if session.get("user_role") != "student":
        flash("权限不足")
        return redirect(url_for('login'))
    user = User.query.get(session["user_id"])
    return render_template("student/profile.html", user=user)

# 搜索老师页面
@app.route('/student/search-teacher', methods=["GET","POST"])
def search_teacher():
    if session.get("user_role") != "student":
        flash("权限不足")
        return redirect(url_for('login'))
    form = SearchTeacherForm()
    target_teacher = None
    is_bind = False
    stu_id = session["user_id"]
    if form.validate_on_submit():
        code = form.teacher_code.data
        target_teacher = User.query.filter_by(role="teacher", teacher_code=code).first()
        if not target_teacher:
            flash("未查询到该身份码对应的老师")
        else:
            # 判断是否已绑定
            rel = TeacherStudentRelate.query.filter_by(teacher_id=target_teacher.id, student_id=stu_id).first()
            if rel:
                is_bind = True
    return render_template("student/search_tea.html", form=form, target_teacher=target_teacher, is_bind=is_bind)

# 绑定老师
@app.route('/student/bind-teacher/<int:tea_id>')
def bind_teacher(tea_id):
    if session.get("user_role") != "student":
        flash("权限不足")
        return redirect(url_for('login'))
    stu_id = session["user_id"]
    tea = User.query.get_or_404(tea_id)
    if tea.role != "teacher":
        flash("该账号不是老师")
        return redirect(url_for('search_teacher'))
    # 查重
    exist = TeacherStudentRelate.query.filter_by(teacher_id=tea_id, student_id=stu_id).first()
    if exist:
        flash("已绑定该老师，无需重复操作")
        return redirect(url_for('search_teacher'))
    new_rel = TeacherStudentRelate(teacher_id=tea_id, student_id=stu_id)
    db.session.add(new_rel)
    db.session.commit()
    flash(f"成功绑定老师 {tea.username}")
    return redirect(url_for('my_teacher'))

# 我的老师列表
@app.route('/student/my-teacher')
def my_teacher():
    if session.get("user_role") != "student":
        flash("权限不足")
        return redirect(url_for('login'))
    stu_id = session["user_id"]
    tea_list = TeacherStudentRelate.query.filter_by(student_id=stu_id).join(User, TeacherStudentRelate.teacher_id == User.id).all()
    return render_template("student/my_teacher.html", tea_list=tea_list)

# 取关解绑老师
@app.route('/student/unbind-teacher/<int:rel_id>')
def unbind_teacher(rel_id):
    if session.get("user_role") != "student":
        flash("权限不足")
        return redirect(url_for('login'))
    rel = TeacherStudentRelate.query.get_or_404(rel_id)
    if rel.student_id != session["user_id"]:
        flash("非法操作")
        return redirect(url_for('my_teacher'))
    db.session.delete(rel)
    db.session.commit()
    flash("已取关该老师")
    return redirect(url_for('my_teacher'))

# 学生绑定老师后，无需考试码，直接根据考试ID报名
@app.route('/student/join-exam-direct/<int:exam_id>')
def join_exam_direct(exam_id):
    if session.get("user_role") != "student":
        flash("权限不足")
        return redirect(url_for('login'))
    stu_id = session["user_id"]
    exam = Exam.query.get_or_404(exam_id)
    now = datetime.datetime.now()

    # 限制：仅绑定该老师的学生才能直接报名
    is_bind = TeacherStudentRelate.query.filter_by(
        teacher_id=exam.creator_id,
        student_id=stu_id
    ).first()
    if not is_bind:
        flash("你未绑定该考试的创建老师，只能通过考试码入场")
        return redirect(url_for('code_exam'))

    # 禁止报名已结束考试
    if exam.is_finish or now > exam.exam_end_time:
        flash("本场考试已结束，无法报名")
        return redirect(url_for('my_teacher'))

    # 检查是否已有答卷记录
    exist_record = ExamRecord.query.filter_by(exam_id=exam_id, student_id=stu_id).first()
    if exist_record:
        flash("你已报名本场考试，可直接进入答题")
        return redirect(url_for('take_exam', record_id=exist_record.id))

    # 创建答卷记录
    new_record = ExamRecord(
        exam_id=exam_id,
        student_id=stu_id,
        answer_content="",
        get_score=0,
        is_submit=False
    )
    db.session.add(new_record)
    db.session.commit()
    flash("报名成功，到开考时间即可答题")
    return redirect(url_for('my_teacher'))

# 查看绑定老师发布的所有考试
@app.route('/student/teacher-exam/<int:tea_id>')
def teacher_exam_list(tea_id):
    if session.get("user_role") != "student":
        flash("权限不足")
        return redirect(url_for('login'))
    stu_id = session["user_id"]
    # 校验是否绑定该老师
    rel = TeacherStudentRelate.query.filter_by(teacher_id=tea_id, student_id=stu_id).first()
    if not rel:
        flash("你未绑定该老师，无法查看考试")
        return redirect(url_for('my_teacher'))
    exam_list = Exam.query.filter_by(creator_id=tea_id).all()
    now = datetime.datetime.now()
    # 实例化表单传给模板，解决form未定义报错
    form = SearchExamCodeForm()
    return render_template("student/code_exam.html", exam_list=exam_list, now=now, form=form)

# 考试码搜索页面
@app.route('/student/code-exam', methods=["GET","POST"])
def code_exam():
    if session.get("user_role") != "student":
        flash("权限不足")
        return redirect(url_for('login'))
    form = SearchExamCodeForm()
    target_exam = None
    record = None
    stu_id = session["user_id"]
    now = datetime.datetime.now()
    if form.validate_on_submit():
        code = form.exam_code.data
        target_exam = Exam.query.filter_by(use_exam_code=True, exam_code=code).first()
        if not target_exam:
            flash("无效考试码，不存在或未启用考试码")
        else:
            # 判断考试码是否过期
            if target_exam.code_expire_time and now > target_exam.code_expire_time:
                flash("该考试码已过期失效")
                target_exam = None
            elif target_exam.is_finish:
                flash("本场考试已结束")
            else:
                # 查询学生是否已有记录
                record = ExamRecord.query.filter_by(exam_id=target_exam.id, student_id=stu_id).first()
    return render_template("student/code_exam.html", form=form, target_exam=target_exam, record=record)

# 通过考试码加入考试，生成答卷记录
@app.route('/student/join-exam/<int:exam_id>')
def join_exam_by_code(exam_id):
    if session.get("user_role") != "student":
        flash("权限不足")
        return redirect(url_for('login'))
    stu_id = session["user_id"]
    exam = Exam.query.get_or_404(exam_id)
    now = datetime.datetime.now()
    # 校验考试状态
    if not exam.use_exam_code or (exam.code_expire_time and now > exam.code_expire_time) or exam.is_finish:
        flash("无法加入本场考试，考试码失效或已结束")
        return redirect(url_for('code_exam'))
    # 判断是否已存在记录
    exist = ExamRecord.query.filter_by(exam_id=exam_id, student_id=stu_id).first()
    if exist:
        flash("你已报名本场考试，可直接进入答题")
        return redirect(url_for('take_exam', record_id=exist.id))
    # 新建答卷记录
    new_record = ExamRecord(
        exam_id=exam_id,
        student_id=stu_id,
        answer_content="",
        get_score=0,
        is_submit=False
    )
    db.session.add(new_record)
    db.session.commit()
    flash("成功报名本场考试，到开考时间即可答题")
    return redirect(url_for('my_exam'))

# 我的全部考试记录
@app.route('/student/my-exam')
def my_exam():
    if session.get("user_role") != "student":
        flash("权限不足")
        return redirect(url_for('login'))
    stu_id = session["user_id"]
    now = datetime.datetime.now()
    record_list = ExamRecord.query.filter_by(student_id=stu_id).join(Exam).order_by(Exam.exam_start_time.desc()).all()
    return render_template("student/my_exam.html", record_list=record_list, now=now)

# 进入答题页面
@app.route('/student/take-exam/<int:record_id>')
def take_exam(record_id):
    if session.get("user_role") != "student":
        flash("权限不足")
        return redirect(url_for('login'))
    stu_id = session["user_id"]
    record = ExamRecord.query.get_or_404(record_id)
    exam = record.exam
    now = datetime.datetime.now()
    # 权限校验：只能访问自己的答卷
    if record.student_id != stu_id:
        flash("非法访问他人试卷")
        return redirect(url_for('my_exam'))
    # 校验考试时间
    if exam.exam_end_time < now:
        flash("考试已结束，无法继续答题")
        return redirect(url_for('my_exam'))
    if record.is_submit:
        flash("你已交卷，无法重复答题")
        return redirect(url_for('score_view', record_id=record.id))
    # 从选中题库ID列表随机抽取题目
    select_q_ids = [int(i) for i in exam.select_q_ids.split(",")]
    all_q = QuestionBank.query.filter(QuestionBank.id.in_(select_q_ids)).all()
    random.shuffle(all_q)
    paper_questions = all_q[:exam.random_pick_num]
    # 是否打乱顺序
    if exam.shuffle_question:
        random.shuffle(paper_questions)
    # 给题目绑定解析答案的方法
    for q in paper_questions:
        def get_opt(self):
            return json.loads(self.options)
        def get_ans(self):
            return json.loads(self.answer)
        q.get_options = get_opt.__get__(q)
        q.get_answer = get_ans.__get__(q)
    return render_template("student/take_exam.html", exam=exam, record=record, paper_questions=paper_questions, form=FlaskForm())

# 提交试卷自动判分
@app.route('/student/submit-exam/<int:record_id>', methods=["POST"])
def submit_exam(record_id):
    if session.get("user_role") != "student":
        flash("权限不足")
        return redirect(url_for('login'))
    stu_id = session["user_id"]
    record = ExamRecord.query.get_or_404(record_id)
    exam = record.exam
    now = datetime.datetime.now()
    if record.student_id != stu_id or record.is_submit or exam.exam_end_time < now:
        flash("提交失败，无效试卷")
        return redirect(url_for('my_exam'))
    select_q_ids = [int(i) for i in exam.select_q_ids.split(",")]
    all_q = QuestionBank.query.filter(QuestionBank.id.in_(select_q_ids)).all()
    random.shuffle(all_q)
    paper_questions = all_q[:exam.random_pick_num]
    if exam.shuffle_question:
        random.shuffle(paper_questions)
    # 收集学生答案
    stu_ans_dict = {}
    total_score = 0
    for q in paper_questions:
        ans_key = f"ans_{q.id}"
        stu_input = request.form.get(ans_key, "")
        stu_ans_dict[q.id] = stu_input
        real_ans = json.loads(q.answer)
        # 判分逻辑
        if q.q_type == "single":
            if stu_input == real_ans:
                total_score += q.score
        elif q.q_type == "judge":
            if str(stu_input).lower() == str(real_ans).lower():
                total_score += q.score
        elif q.q_type == "blank":
            if stu_input.strip() == real_ans.strip():
                total_score += q.score
        elif q.q_type == "multi":
            stu_arr = stu_input.split(",") if stu_input else []
            real_arr = real_ans
            if set(stu_arr) == set(real_arr):
                total_score += q.score
    # 更新答卷记录
    record.answer_content = json.dumps(stu_ans_dict)
    record.get_score = total_score
    record.is_submit = True
    record.submit_time = now
    db.session.commit()
    flash(f"交卷成功！本次得分：{total_score}")
    return redirect(url_for('score_view', record_id=record.id))

# 查看成绩与标准答案
@app.route('/student/score-view/<int:record_id>')
def score_view(record_id):
    if session.get("user_role") != "student":
        flash("权限不足")
        return redirect(url_for('login'))
    stu_id = session["user_id"]
    record = ExamRecord.query.get_or_404(record_id)
    exam = record.exam
    if record.student_id != stu_id or not record.is_submit:
        flash("无权限查看该成绩")
        return redirect(url_for('my_exam'))
    stu_answers = json.loads(record.answer_content) if record.answer_content else {}
    # 还原试卷题目
    select_q_ids = [int(i) for i in exam.select_q_ids.split(",")]
    all_q = QuestionBank.query.filter(QuestionBank.id.in_(select_q_ids)).all()
    random.shuffle(all_q)
    paper_questions = all_q[:exam.random_pick_num]
    if exam.shuffle_question:
        random.shuffle(paper_questions)
    # 绑定解析方法
    for q in paper_questions:
        def get_opt(self):
            return json.loads(self.options)
        def get_ans(self):
            return json.loads(self.answer)
        q.get_options = get_opt.__get__(q)
        q.get_answer = get_ans.__get__(q)
    return render_template("student/score_view.html", exam=exam, record=record, paper_questions=paper_questions, student_answers=stu_answers)

# ====================== 程序启动入口 ======================
if __name__ == '__main__':
    # 首次运行请取消下面两行注释，运行一次生成数据库后再注释
    #create_db()
    app.run(debug=True, host="127.0.0.1", port=5000)