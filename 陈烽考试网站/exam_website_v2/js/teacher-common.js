function initTeacherPage() {
    if (!Auth.checkAuth() || Auth.getUserType() !== 'teacher') {
        window.location.href = '../../index.html'; return;
    }
    const user = Auth.getUser();
    const el = document.getElementById('teacherName');
    if (el) el.textContent = user.name;
    const currentPage = window.location.pathname.split('/').pop();
    document.querySelectorAll('.nav-menu a').forEach(link => {
        if (link.getAttribute('href').includes(currentPage)) link.classList.add('active');
    });
}
function logout() { Auth.logout(); }
function confirmAction(message, callback) { if (confirm(message)) callback(); }
function showToast(message, type) {
    const toast = document.createElement('div');
    toast.style.cssText = `position:fixed;top:20px;right:20px;padding:15px 25px;background:${type==='success'?'#2ecc71':'#e74c3c'};color:white;border-radius:8px;z-index:9999;font-weight:600;`;
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}
