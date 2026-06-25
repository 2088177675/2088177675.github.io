let currentTab = 'student';
function switchTab(type) {
    currentTab = type;
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    event.target.classList.add('active');
    const classSelect = document.getElementById('classSelect');
    if (type === 'student') { classSelect.style.display = 'block'; loadClasses(); }
    else { classSelect.style.display = 'none'; }
}
function loadClasses() {
    const classes = DataStore.get('classes');
    const select = document.getElementById('classId');
    select.innerHTML = '<option value="">-- 请选择班级 --</option>';
    classes.forEach(c => { select.innerHTML += `<option value="${c.id}">${c.name}</option>`; });
}
function handleLogin(event) {
    event.preventDefault();
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    const result = Auth.login(username, password, currentTab);
    if (result.success) {
        if (currentTab === 'teacher') { window.location.href = 'pages/teacher/dashboard.html'; }
        else {
            const classId = document.getElementById('classId').value;
            if (!classId) { alert('请选择班级'); return; }
            sessionStorage.setItem('studentClassId', classId);
            window.location.href = 'pages/student/dashboard.html';
        }
    } else { alert(result.message); }
}
document.addEventListener('DOMContentLoaded', () => { loadClasses(); });
