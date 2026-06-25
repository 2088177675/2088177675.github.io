const DataStore = {
    init() {
        if (!localStorage.getItem('exam_system_initialized')) {
            const classes = [
                { id: 1, name: '软件工程1班', description: '2024级软件工程专业', studentCount: 0 },
                { id: 2, name: '计算机科学2班', description: '2024级计算机科学专业', studentCount: 0 },
                { id: 3, name: '网络工程1班', description: '2024级网络工程专业', studentCount: 0 }
            ];
            const students = [
                { id: 1, username: 'student1', password: '123456', name: '张三', classId: 1, className: '软件工程1班' },
                { id: 2, username: 'student2', password: '123456', name: '李四', classId: 1, className: '软件工程1班' },
                { id: 3, username: 'student3', password: '123456', name: '王五', classId: 2, className: '计算机科学2班' },
                { id: 4, username: 'student4', password: '123456', name: '赵六', classId: 2, className: '计算机科学2班' },
                { id: 5, username: 'student5', password: '123456', name: '钱七', classId: 3, className: '网络工程1班' }
            ];
            const teachers = [{ id: 1, username: 'teacher', password: '123456', name: '王老师' }];
            const exams = [
                {
                    id: 1, title: 'JavaScript基础测试', description: '考察JavaScript基础知识掌握情况',
                    classId: 1, className: '软件工程1班', duration: 60, totalScore: 100, status: 'published',
                    createTime: '2024-01-15 10:00',
                    questions: [
                        { id: 1, type: 'single', content: 'JavaScript中，以下哪个不是基本数据类型？', options: ['String', 'Number', 'Array', 'Boolean'], correctAnswer: 2, score: 20, explanation: 'Array是引用类型，不是基本数据类型。基本数据类型包括：String、Number、Boolean、Null、Undefined、Symbol。' },
                        { id: 2, type: 'single', content: '以下哪个方法可以将字符串转换为数字？', options: ['toString()', 'parseInt()', 'split()', 'join()'], correctAnswer: 1, score: 20, explanation: 'parseInt()和parseFloat()可以将字符串转换为数字。' },
                        { id: 3, type: 'single', content: '在JavaScript中，=== 和 == 的区别是什么？', options: ['没有区别', '===比较值和类型，==只比较值', '===只比较类型', '==比较值和类型'], correctAnswer: 1, score: 20, explanation: '===是严格相等运算符，比较值和类型；==是相等运算符，会进行类型转换后比较值。' },
                        { id: 4, type: 'single', content: '以下哪个不是JavaScript的循环语句？', options: ['for', 'while', 'loop', 'do...while'], correctAnswer: 2, score: 20, explanation: 'JavaScript中的循环语句包括：for、while、do...while、for...in、for...of，没有loop语句。' },
                        { id: 5, type: 'single', content: 'JavaScript中，数组的push()方法的作用是？', options: ['删除最后一个元素', '在末尾添加一个或多个元素', '在开头添加元素', '删除第一个元素'], correctAnswer: 1, score: 20, explanation: 'push()方法在数组末尾添加一个或多个元素，并返回新数组的长度。' }
                    ]
                },
                {
                    id: 2, title: 'HTML/CSS基础测试', description: '考察HTML和CSS基础知识',
                    classId: 2, className: '计算机科学2班', duration: 45, totalScore: 100, status: 'published',
                    createTime: '2024-01-16 14:00',
                    questions: [
                        { id: 1, type: 'single', content: 'HTML中，哪个标签用于定义最大的标题？', options: ['<h6>', '<head>', '<h1>', '<header>'], correctAnswer: 2, score: 25, explanation: '<h1>到<h6>定义标题，<h1>是最大的标题。' },
                        { id: 2, type: 'single', content: 'CSS中，哪个属性用于改变文本颜色？', options: ['text-color', 'font-color', 'color', 'foreground'], correctAnswer: 2, score: 25, explanation: 'CSS中使用color属性设置文本颜色。' },
                        { id: 3, type: 'single', content: '在CSS中，选择器 .box 选择的是？', options: ['id为box的元素', 'class为box的元素', '标签为box的元素', 'name为box的元素'], correctAnswer: 1, score: 25, explanation: '.box是类选择器，选择class属性包含box的元素。' },
                        { id: 4, type: 'single', content: 'HTML5中，哪个标签用于定义文档的主要内容？', options: ['<section>', '<main>', '<article>', '<div>'], correctAnswer: 1, score: 25, explanation: '<main>标签定义文档的主要内容。' }
                    ]
                }
            ];
            const scores = [
                { id: 1, studentId: 1, studentName: '张三', examId: 1, examTitle: 'JavaScript基础测试', className: '软件工程1班', score: 80, totalScore: 100, answers: [2, 1, 1, 0, 1], submitTime: '2024-01-15 11:30', duration: 35 },
                { id: 2, studentId: 2, studentName: '李四', examId: 1, examTitle: 'JavaScript基础测试', className: '软件工程1班', score: 60, totalScore: 100, answers: [2, 0, 1, 2, 1], submitTime: '2024-01-15 11:45', duration: 42 }
            ];
            localStorage.setItem('classes', JSON.stringify(classes));
            localStorage.setItem('students', JSON.stringify(students));
            localStorage.setItem('teachers', JSON.stringify(teachers));
            localStorage.setItem('exams', JSON.stringify(exams));
            localStorage.setItem('scores', JSON.stringify(scores));
            localStorage.setItem('exam_system_initialized', 'true');
        }
    },
    get(key) { const data = localStorage.getItem(key); return data ? JSON.parse(data) : []; },
    set(key, value) { localStorage.setItem(key, JSON.stringify(value)); },
    generateId(key) { const items = this.get(key); return items.length > 0 ? Math.max(...items.map(i => i.id)) + 1 : 1; }
};
DataStore.init();
