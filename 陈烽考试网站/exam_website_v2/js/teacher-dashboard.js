document.addEventListener('DOMContentLoaded', () => {
    initTeacherPage(); loadStats(); loadRecentExams(); loadRecentScores();
});
function loadStats() {
    document.getElementById('examCount').textContent = DataStore.get('exams').length;
    document.getElementById('studentCount').textContent = DataStore.get('students').length;
    document.getElementById('classCount').textContent = DataStore.get('classes').length;
    document.getElementById('scoreCount').textContent = DataStore.get('scores').length;
}
function loadRecentExams() {
    const exams = DataStore.get('exams').slice(-5).reverse();
    const tbody = document.getElementById('recentExams');
    if (exams.length === 0) { tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:#888;">暂无考试</td></tr>'; return; }
    tbody.innerHTML = exams.map(exam => `<tr><td><strong>${exam.title}</strong></td><td>${exam.className}</td><td>${exam.duration}分钟</td><td>${exam.totalScore}分</td><td><span class="badge ${exam.status==='published'?'badge-success':'badge-warning'}">${exam.status==='published'?'已发布':'草稿'}</span></td><td>${exam.createTime}</td></tr>`).join('');
}
function loadRecentScores() {
    const scores = DataStore.get('scores').slice(-5).reverse();
    const tbody = document.getElementById('recentScores');
    if (scores.length === 0) { tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:#888;">暂无成绩</td></tr>'; return; }
    tbody.innerHTML = scores.map(s => `<tr><td>${s.studentName}</td><td>${s.examTitle}</td><td>${s.className}</td><td><strong style="color:${s.score>=60?'#2ecc71':'#e74c3c'}">${s.score}</strong>/${s.totalScore}</td><td>${s.duration}分钟</td><td>${s.submitTime}</td></tr>`).join('');
}
