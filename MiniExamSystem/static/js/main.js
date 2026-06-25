// 通用倒计时工具
function startCountdown(elementId, targetTimeStr) {
    const el = document.getElementById(elementId);
    if (!el) return;

    const target = new Date(targetTimeStr).getTime();
    setInterval(() => {
        const now = Date.now();
        const diff = target - now;
        if (diff <= 0) {
            el.innerHTML = "<span style='color:red'>已过期</span>";
            return;
        }
        const day = Math.floor(diff / (1000 * 60 * 60 * 24));
        const hour = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
        const min = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
        const sec = Math.floor((diff % (1000 * 60)) / 1000);
        el.innerHTML = `<span class="countdown-num">${day}天 ${hour}时 ${min}分 ${sec}秒</span>`;
    }, 1000);
}

// 批量全选/取消题库复选框
function checkAll(checkboxName, isCheck) {
    const inputs = document.querySelectorAll(`input[name="${checkboxName}"]`);
    inputs.forEach(item => item.checked = isCheck);
}

// 表单通用校验
function checkEmpty(inputId, tipText) {
    const input = document.getElementById(inputId);
    if (!input.value.trim()) {
        alert(tipText);
        input.focus();
        return false;
    }
    return true;
}

// 6位验证码/考试码校验（仅字母数字）
function checkSixCode(val) {
    const reg = /^[A-Za-z0-9]{6}$/;
    return reg.test(val);
}

// 提交前弹窗确认删除
function confirmDel(msg) {
    return window.confirm(msg || "确定要删除这条数据吗？删除后不可恢复！");
}

// 页面加载完成后执行
window.onload = function () {
    // 自动隐藏提示消息，3秒消失
    const flashBox = document.querySelector(".flash-box");
    if (flashBox) {
        setTimeout(() => {
            flashBox.style.display = "none";
        }, 3000);
    }
}