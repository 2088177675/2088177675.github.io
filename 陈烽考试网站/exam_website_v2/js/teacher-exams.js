let questionCount = 0;

// ========== DeepSeek API 配置 ==========
// ⚠️ 使用方式：把 sk-你的API密钥 替换为你的真实 DeepSeek API Key
// 获取地址：https://platform.deepseek.com → API Keys → 创建 API Key
const DEEPSEEK_API_KEY = 'sk-e203bb772d31422bac3e8e480720ace6';
const DEEPSEEK_API_URL = 'https://api.deepseek.com/chat/completions';

document.addEventListener('DOMContentLoaded', () => { initTeacherPage(); loadClasses(); loadExams(); });

function loadClasses() {
    const classes = DataStore.get('classes');
    const selects = document.querySelectorAll('#examClass, #filterClass');
    selects.forEach(select => {
        if (select.id === 'filterClass') select.innerHTML = '<option value="">全部班级</option>';
        classes.forEach(c => { select.innerHTML += `<option value="${c.id}">${c.name}</option>`; });
    });
}

function loadExams() {
    let exams = DataStore.get('exams');
    const search = document.getElementById('searchExam').value.toLowerCase();
    const classFilter = document.getElementById('filterClass').value;
    const statusFilter = document.getElementById('filterStatus').value;
    let filtered = exams.filter(e => {
        if (search && !e.title.toLowerCase().includes(search)) return false;
        if (classFilter && e.classId != classFilter) return false;
        if (statusFilter && e.status !== statusFilter) return false;
        return true;
    });
    const tbody = document.getElementById('examsTable');
    if (filtered.length === 0) { tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;color:#888;">暂无考试数据</td></tr>'; return; }
    tbody.innerHTML = filtered.map(exam => `<tr><td><strong>${exam.title}</strong></td><td>${exam.className}</td><td>${exam.duration}</td><td>${exam.totalScore}</td><td>${exam.questions?.length||0}</td><td><span class="badge ${exam.status==='published'?'badge-success':'badge-warning'}">${exam.status==='published'?'已发布':'草稿'}</span></td><td>${exam.createTime}</td><td><button class="btn btn-primary btn-sm" onclick="viewExam(${exam.id})">查看</button> <button class="btn btn-danger btn-sm" onclick="deleteExam(${exam.id})">删除</button></td></tr>`).join('');
}

function filterExams() { loadExams(); }

function openExamModal() {
    document.getElementById('examTitle').value = '';
    document.getElementById('examClass').value = '';
    document.getElementById('examDuration').value = '';
    document.getElementById('examTotalScore').value = '';
    document.getElementById('examDesc').value = '';
    document.getElementById('questionsContainer').innerHTML = '';
    questionCount = 0; addQuestion();
    document.getElementById('examModal').classList.add('active');
}

function closeExamModal() { document.getElementById('examModal').classList.remove('active'); }

function addQuestion() {
    questionCount++;
    const container = document.getElementById('questionsContainer');
    const div = document.createElement('div');
    div.className = 'question-item';
    div.innerHTML = `<div class="question-header"><h4>题目 ${questionCount}</h4><button type="button" class="btn btn-danger btn-sm" onclick="this.closest('.question-item').remove()">删除</button></div><div class="form-group"><label>题目内容 *</label><textarea class="q-content" rows="2" placeholder="请输入题目内容" required></textarea></div><div class="form-row"><div class="form-group"><label>分值 *</label><input type="number" class="q-score" placeholder="分值" min="1" required></div><div class="form-group"><label>正确答案选项 *</label><select class="q-correct" required><option value="">选择答案</option><option value="0">A</option><option value="1">B</option><option value="2">C</option><option value="3">D</option></select></div></div><div class="form-group"><label>选项A *</label><input type="text" class="q-opt-0" placeholder="选项A" required></div><div class="form-group"><label>选项B *</label><input type="text" class="q-opt-1" placeholder="选项B" required></div><div class="form-group"><label>选项C *</label><input type="text" class="q-opt-2" placeholder="选项C" required></div><div class="form-group"><label>选项D *</label><input type="text" class="q-opt-3" placeholder="选项D" required></div><div class="form-group"><label>答案解析</label><textarea class="q-explain" rows="2" placeholder="请输入答案解析..."></textarea></div>`;
    container.appendChild(div);
}

function saveExam() {
    const title = document.getElementById('examTitle').value;
    const classId = document.getElementById('examClass').value;
    const duration = document.getElementById('examDuration').value;
    const totalScore = document.getElementById('examTotalScore').value;
    const desc = document.getElementById('examDesc').value;
    if (!title || !classId || !duration || !totalScore) { alert('请填写完整的考试信息'); return; }
    const classes = DataStore.get('classes');
    const classInfo = classes.find(c => c.id == classId);
    const questions = [];
    let qIndex = 1;
    document.querySelectorAll('.question-item').forEach(item => {
        const content = item.querySelector('.q-content').value;
        const score = item.querySelector('.q-score').value;
        const correct = item.querySelector('.q-correct').value;
        const explain = item.querySelector('.q-explain').value;
        if (!content || !score || correct === '') { alert(`请完善题目 ${qIndex} 的信息`); return; }
        const options = [item.querySelector('.q-opt-0').value, item.querySelector('.q-opt-1').value, item.querySelector('.q-opt-2').value, item.querySelector('.q-opt-3').value];
        questions.push({ id: qIndex, type: 'single', content, options, correctAnswer: parseInt(correct), score: parseInt(score), explanation: explain });
        qIndex++;
    });
    if (questions.length === 0) { alert('请至少添加一道题目'); return; }
    const exams = DataStore.get('exams');
    exams.push({ id: DataStore.generateId('exams'), title, description: desc, classId: parseInt(classId), className: classInfo.name, duration: parseInt(duration), totalScore: parseInt(totalScore), status: 'published', createTime: new Date().toLocaleString('zh-CN'), questions });
    DataStore.set('exams', exams);
    showToast('考试发布成功！');
    closeExamModal(); loadExams();
}

function viewExam(id) {
    const exam = DataStore.get('exams').find(e => e.id === id);
    if (!exam) return;
    let questionsHtml = exam.questions.map((q, i) => `<div style="margin-bottom:20px;padding:15px;background:#f8f9fa;border-radius:8px;"><p><strong>题目 ${i+1}</strong> (${q.score}分)</p><p>${q.content}</p><div style="margin:10px 0;padding-left:20px;">${q.options.map((opt, j) => `<p style="color:${j===q.correctAnswer?'#2ecc71':'#555'};font-weight:${j===q.correctAnswer?'600':'normal'}">${String.fromCharCode(65+j)}. ${opt} ${j===q.correctAnswer?'✓ 正确答案':''}</p>`).join('')}</div>${q.explanation?`<p style="color:#667eea;font-size:13px;">💡 解析：${q.explanation}</p>`:''}</div>`).join('');
    document.getElementById('detailContent').innerHTML = `<h4>${exam.title}</h4><p style="color:#888;margin-bottom:15px;">${exam.description||'暂无说明'}</p><div class="form-row" style="margin-bottom:20px;"><div><strong>班级：</strong>${exam.className}</div><div><strong>时长：</strong>${exam.duration}分钟</div><div><strong>总分：</strong>${exam.totalScore}分</div><div><strong>题目数：</strong>${exam.questions.length}道</div></div><h4 style="margin-bottom:15px;">题目列表</h4>${questionsHtml}`;
    document.getElementById('detailModal').classList.add('active');
}

function closeDetailModal() { document.getElementById('detailModal').classList.remove('active'); }

function deleteExam(id) {
    confirmAction('确定要删除这场考试吗？相关成绩也将被删除！', () => {
        let exams = DataStore.get('exams'); exams = exams.filter(e => e.id !== id); DataStore.set('exams', exams);
        let scores = DataStore.get('scores'); scores = scores.filter(s => s.examId !== id); DataStore.set('scores', scores);
        showToast('考试已删除'); loadExams();
    });
}

// ========== AI 自动出题功能（DeepSeek） ==========

function openAIModal() { document.getElementById('aiModal').classList.add('active'); }
function closeAIModal() { document.getElementById('aiModal').classList.remove('active'); }

async function generateQuestions() {
    const topic = document.getElementById('aiTopic').value.trim();
    const subject = document.getElementById('aiSubject').value;
    const count = parseInt(document.getElementById('aiCount').value);
    const difficulty = document.getElementById('aiDifficulty').value;

    if (!topic) { alert('请输入出题主题！'); return; }
    if (DEEPSEEK_API_KEY === 'sk-你的API密钥') {
        alert('请先设置 DeepSeek API Key！\n\n1. 访问 https://platform.deepseek.com 注册并获取 API Key\n2. 打开 js/teacher-exams.js 文件\n3. 把第 6 行的 sk-你的API密钥 替换为你的真实 API Key');
        return;
    }

    const btn = document.getElementById('aiGenerateBtn');
    const originalText = btn.innerHTML;
    btn.innerHTML = '<span class="ai-loading"></span>AI 正在出题中...';
    btn.disabled = true;

    try {
        const prompt = `请为"${topic}"这个主题生成 ${count} 道${difficulty}难度的单选题。
要求：
1. 每道题包含：题目内容、4个选项(A/B/C/D)、正确答案(0/1/2/3对应A/B/C/D)、分值(建议20-25分)、答案解析
2. 选项要有干扰性，不能过于简单
3. 题目要专业、准确
4. 请严格按照以下JSON格式返回，不要添加任何其他文字：

[
  {
    "content": "题目内容",
    "options": ["选项A", "选项B", "选项C", "选项D"],
    "correctAnswer": 0,
    "score": 20,
    "explanation": "答案解析"
  }
]`;

        const response = await fetch(DEEPSEEK_API_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${DEEPSEEK_API_KEY}`
            },
            body: JSON.stringify({
                model: 'deepseek-chat',
                messages: [
                    { role: 'system', content: '你是一位专业的教育出题专家，擅长生成高质量的考试题目。' },
                    { role: 'user', content: prompt }
                ],
                temperature: 0.7,
                max_tokens: 4000,
                stream: false
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error?.message || `API 调用失败 (状态码: ${response.status})`);
        }

        const data = await response.json();
        const aiResponse = data.choices[0].message.content;

        let questions;
        try {
            const jsonMatch = aiResponse.match(/\[[\s\S]*\]/);
            if (jsonMatch) { questions = JSON.parse(jsonMatch[0]); }
            else { questions = JSON.parse(aiResponse); }
        } catch (e) {
            console.error('AI 返回内容:', aiResponse);
            throw new Error('AI 返回格式不正确，请重试。如果多次失败，请检查 API Key 是否有效。');
        }

        addAIGeneratedQuestions(questions);
        closeAIModal();
        showToast(`✅ 成功生成 ${questions.length} 道题目！`);

    } catch (error) {
        alert('AI 出题失败：' + error.message);
        console.error('完整错误:', error);
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}

function addAIGeneratedQuestions(questions) {
    const container = document.getElementById('questionsContainer');
    questions.forEach((q) => {
        questionCount++;
        const div = document.createElement('div');
        div.className = 'question-item active';
        div.innerHTML = `<div class="question-header"><h4>题目 ${questionCount} <span class="ai-badge">🤖 AI</span></h4><button type="button" class="btn btn-danger btn-sm" onclick="this.closest('.question-item').remove()">删除</button></div><div class="form-group"><label>题目内容 *</label><textarea class="q-content" rows="2" required>${q.content||''}</textarea></div><div class="form-row"><div class="form-group"><label>分值 *</label><input type="number" class="q-score" value="${q.score||20}" min="1" required></div><div class="form-group"><label>正确答案选项 *</label><select class="q-correct" required><option value="">选择答案</option><option value="0" ${q.correctAnswer===0?'selected':''}>A</option><option value="1" ${q.correctAnswer===1?'selected':''}>B</option><option value="2" ${q.correctAnswer===2?'selected':''}>C</option><option value="3" ${q.correctAnswer===3?'selected':''}>D</option></select></div></div><div class="form-group"><label>选项A *</label><input type="text" class="q-opt-0" value="${q.options?.[0]||''}" required></div><div class="form-group"><label>选项B *</label><input type="text" class="q-opt-1" value="${q.options?.[1]||''}" required></div><div class="form-group"><label>选项C *</label><input type="text" class="q-opt-2" value="${q.options?.[2]||''}" required></div><div class="form-group"><label>选项D *</label><input type="text" class="q-opt-3" value="${q.options?.[3]||''}" required></div><div class="form-group"><label>答案解析</label><textarea class="q-explain" rows="2">${q.explanation||''}</textarea></div>`;
        container.appendChild(div);
    });
}
