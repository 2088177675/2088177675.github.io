function initStudentPage() {
    if (!Auth.checkAuth() || Auth.getUserType() !== 'student') {
        window.location.href = '../../index.html'; return;
    }
    const user = Auth.getUser();
    const el = document.getElementById('studentName');
    if (el) el.textContent = user.name;
    const currentPage = window.location.pathname.split('/').pop();
    document.querySelectorAll('.nav-menu a').forEach(link => {
        if (link.getAttribute('href').includes(currentPage)) link.classList.add('active');
    });
}
function logout() { Auth.logout(); }
