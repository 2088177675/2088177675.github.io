const Auth = {
    currentUser: null, userType: null,
    login(username, password, type) {
        let users = DataStore.get(type === 'teacher' ? 'teachers' : 'students');
        const user = users.find(u => u.username === username && u.password === password);
        if (user) {
            this.currentUser = user; this.userType = type;
            sessionStorage.setItem('currentUser', JSON.stringify(user));
            sessionStorage.setItem('userType', type);
            return { success: true, user };
        }
        return { success: false, message: '账号或密码错误' };
    },
    checkAuth() {
        const user = sessionStorage.getItem('currentUser');
        const type = sessionStorage.getItem('userType');
        if (user && type) { this.currentUser = JSON.parse(user); this.userType = type; return true; }
        return false;
    },
    logout() {
        this.currentUser = null; this.userType = null;
        sessionStorage.removeItem('currentUser');
        sessionStorage.removeItem('userType');
        sessionStorage.removeItem('studentClassId');
        // 根据当前页面深度决定跳转路径
        const path = window.location.pathname;
        if (path.includes('/pages/teacher/') || path.includes('/pages/student/')) {
            window.location.href = '../../index.html';
        } else {
            window.location.href = 'index.html';
        }
    },
    getUser() { if (!this.currentUser) this.checkAuth(); return this.currentUser; },
    getUserType() { if (!this.userType) this.checkAuth(); return this.userType; }
};
