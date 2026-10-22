import { createRouter, createWebHashHistory } from 'vue-router'
import { useAppStore } from '../store'

const roleMenus = {
  1: [
    { path: '/admin/overview', label: '数据概览' },
    { path: '/admin/school', label: '学校管理' },
    { path: '/admin/dept', label: '院系/专业/班级' },
    { path: '/admin/user', label: '用户管理' },
    { path: '/admin/student', label: '学生管理' },
    { path: '/admin/teacher', label: '导师管理' },
    { path: '/admin/ability', label: '能力管理' },
    { path: '/admin/notice', label: '通知管理' },
    {
      path: '/admin/me',
      label: '我的信息',
      children: [
        { path: '/admin/me/profile', label: '个人信息' },
        { path: '/admin/me/security', label: '安全信息' }
      ]
    }
  ],
  2: [
    { path: '/teacher/home', label: '首页' },
    { path: '/teacher/workbench', label: '工作台' },
    { path: '/teacher/messages', label: '留言信息' },
    { path: '/teacher/notice/mine', label: '通知' },
    { path: '/teacher/student-search', label: '学生查询' },
    { path: '/teacher/my-students', label: '我的学生' },
    { path: '/teacher/evaluation', label: '能力评价' },
    { path: '/teacher/assistant', label: '学业 AI 助手' },
    {
      path: '/teacher/me',
      label: '我的信息',
      children: [
        { path: '/teacher/me/profile', label: '个人信息' },
        { path: '/teacher/me/teacher', label: '导师信息' },
        { path: '/teacher/me/security', label: '安全信息' }
      ]
    }
  ],
  3: [
    { path: '/student/home', label: '首页' },
    { path: '/student/my-teacher', label: '我的导师' },
    {
      path: '/student/my-material',
      label: '我的材料',
      children: [
        { path: '/student/my-material', label: '材料列表' },
        { path: '/student/my-material/create', label: '添加材料' }
      ]
    },
    { path: '/student/message', label: '留言信息' },
    {
      path: '/student/me',
      label: '我的信息',
      children: [
        { path: '/student/me/profile', label: '个人信息' },
        { path: '/student/me/academic', label: '学籍信息' },
        { path: '/student/me/security', label: '安全信息' }
      ]
    }
  ]
}

function roleHomePath(roleId) {
  if (roleId === 1) return '/admin/me/profile'
  if (roleId === 2) return '/teacher/home'
  return '/student/home'
}

function roleNoticePath(roleId) {
  if (roleId === 1) return roleHomePath(roleId)
  if (roleId === 2) return '/teacher/notice/mine'
  return roleHomePath(roleId)
}

function roleSchoolPath(roleId) {
  if (roleId === 1) return roleHomePath(roleId)
  return roleHomePath(roleId)
}

const routes = [
  { path: '/', redirect: '/login' },
  {
    path: '/app',
    component: () => import('../views/AppLayout.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/admin',
    component: () => import('../views/AppLayout.vue'),
    meta: { requiresAuth: true, roles: [1], homePath: '/admin/me/profile', menuItems: roleMenus[1] },
    redirect: '/admin/me/profile',
    children: [
      { path: 'overview', component: () => import('../views/AdminOverviewPage.vue'), meta: { title: '数据概览' } },
      { path: 'school', component: () => import('../views/AdminSchoolHierarchyPage.vue'), meta: { title: '学校管理' } },
      { path: 'dept', component: () => import('../views/AdminDeptHierarchyPage.vue'), meta: { title: '院系/专业/班级' } },
      { path: 'user', component: () => import('../views/AdminUserPage.vue'), meta: { title: '用户管理' } },
      { path: 'student', component: () => import('../views/AdminStudentPage.vue'), meta: { title: '学生管理' } },
      { path: 'teacher', component: () => import('../views/AdminTeacherPage.vue'), meta: { title: '导师管理' } },
      { path: 'ability', component: () => import('../views/AdminAbilityPage.vue'), meta: { title: '能力管理' } },
      { path: 'notice', component: () => import('../views/AdminNoticePage.vue'), meta: { title: '通知管理' } },
      {
        path: 'ability/:id',
        component: () => import('../views/AdminAbilityDetail.vue'),
        meta: { title: '材料查看', activeMenu: '/admin/ability' }
      },
      {
        path: 'teacher/:id/edit',
        component: () => import('../views/AdminTeacherEdit.vue'),
        meta: { title: '修改导师', activeMenu: '/admin/teacher' }
      },
      {
        path: 'student/:id/edit',
        component: () => import('../views/AdminStudentEdit.vue'),
        meta: { title: '修改学生', activeMenu: '/admin/student' }
      },
      {
        path: 'user/:id',
        component: () => import('../views/AdminUserDetail.vue'),
        meta: { title: '用户详情', activeMenu: '/admin/user' }
      },
      {
        path: 'user/:id/edit',
        component: () => import('../views/AdminUserEdit.vue'),
        meta: { title: '修改用户', activeMenu: '/admin/user' }
      },
      { path: 'me', redirect: '/admin/me/profile' },
      { path: 'me/profile', component: () => import('../views/MyInfoPage.vue'), meta: { title: '个人信息' } },
      { path: 'me/profile/edit', component: () => import('../views/MyInfoPage.vue'), meta: { title: '修改信息', mode: 'edit' } },
      { path: 'me/security', component: () => import('../views/MyInfoPage.vue'), meta: { title: '安全信息' } }
    ]
  },
  {
    path: '/teacher',
    component: () => import('../views/AppLayout.vue'),
    meta: { requiresAuth: true, roles: [2], homePath: '/teacher/home', menuItems: roleMenus[2] },
    redirect: '/teacher/home',
    children: [
      { path: 'home', component: () => import('../views/AppHome.vue') },
      { path: 'workbench', component: () => import('../views/TeacherWorkbench.vue'), meta: { title: '工作台' } },
      { path: 'messages', component: () => import('../views/MessagesPage.vue'), meta: { title: '留言信息' } },
      { path: 'notice/mine', component: () => import('../views/NoticeMine.vue') },
      { path: 'student-search', component: () => import('../views/TeacherStudentSearch.vue'), meta: { title: '学生查询' } },
      { path: 'my-students', component: () => import('../views/TeacherStudentSearch.vue'), meta: { title: '我的学生', mode: 'my-students' } },
      { path: 'evaluation', component: () => import('../views/TeacherEvaluationPage.vue'), meta: { title: '能力评价' } },
      { path: 'assistant', component: () => import('../views/TeacherAssistantPage.vue'), meta: { title: '学业 AI 助手' } },
      {
        path: 'evaluation/:id',
        component: () => import('../views/TeacherEvaluationDetail.vue'),
        meta: { title: '材料查看', activeMenu: '/teacher/evaluation' }
      },
      {
        path: 'my-students/:id',
        component: () => import('../views/TeacherStudentDetail.vue'),
        meta: { title: '学生信息', activeMenu: '/teacher/my-students' }
      },
      { path: 'me', redirect: '/teacher/me/profile' },
      { path: 'me/profile', component: () => import('../views/MyInfoPage.vue'), meta: { title: '个人信息' } },
      { path: 'me/profile/edit', component: () => import('../views/MyInfoPage.vue'), meta: { title: '修改信息', mode: 'edit' } },
      { path: 'me/academic', redirect: '/teacher/me/teacher' },
      { path: 'me/teacher', component: () => import('../views/MyInfoPage.vue'), meta: { title: '导师信息' } },
      {
        path: 'me/teacher/create',
        component: () => import('../views/MyInfoPage.vue'),
        meta: { title: '完善导师信息', mode: 'teacher-create', activeMenu: '/teacher/me/teacher' }
      },
      { path: 'me/teacher/edit', component: () => import('../views/MyInfoPage.vue'), meta: { title: '修改导师信息', mode: 'teacher-edit' } },
      { path: 'me/security', component: () => import('../views/MyInfoPage.vue'), meta: { title: '安全信息' } }
    ]
  },
  {
    path: '/student',
    component: () => import('../views/AppLayout.vue'),
    meta: { requiresAuth: true, roles: [3], homePath: '/student/home', menuItems: roleMenus[3] },
    redirect: '/student/home',
    children: [
      { path: 'home', component: () => import('../views/AppHome.vue') },
      { path: 'my-teacher', component: () => import('../views/MyInfoPage.vue'), meta: { title: '我的导师' } },
      { path: 'my-material', component: () => import('../views/MyInfoPage.vue'), meta: { title: '我的材料' } },
      {
        path: 'my-material/create',
        component: () => import('../views/StudentMaterialCreate.vue'),
        meta: { title: '材料上传', activeMenu: '/student/my-material' }
      },
      {
        path: 'my-material/:id/edit',
        component: () => import('../views/StudentMaterialCreate.vue'),
        meta: { title: '材料修改', activeMenu: '/student/my-material' }
      },
      {
        path: 'my-material/:id',
        component: () => import('../views/StudentMaterialDetail.vue'),
        meta: { title: '材料查看', activeMenu: '/student/my-material' }
      },
      { path: 'message', component: () => import('../views/MessagesPage.vue'), meta: { title: '留言信息' } },
      { path: 'me', redirect: '/student/me/profile' },
      { path: 'me/profile', component: () => import('../views/MyInfoPage.vue'), meta: { title: '个人信息' } },
      { path: 'me/profile/edit', component: () => import('../views/MyInfoPage.vue'), meta: { title: '修改信息', mode: 'edit' } },
      { path: 'me/academic', component: () => import('../views/MyInfoPage.vue'), meta: { title: '学籍信息' } },
      { path: 'me/academic/create', component: () => import('../views/MyInfoPage.vue'), meta: { title: '完善学籍信息', mode: 'academic-create' } },
      { path: 'me/academic/edit', component: () => import('../views/MyInfoPage.vue'), meta: { title: '修改学籍信息', mode: 'academic-edit' } },
      { path: 'me/security', component: () => import('../views/MyInfoPage.vue'), meta: { title: '安全信息' } }
    ]
  },
  {
    path: '/notice/mine',
    redirect: '/app'
  },
  {
    path: '/school',
    redirect: '/app'
  },
  {
    path: '/login',
    component: () => import('../views/Login.vue')
  },
  {
    path: '/register',
    component: () => import('../views/Register.vue')
  },
  {
    path: '/forget-password',
    component: () => import('../views/ForgetPassword.vue')
  }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes
})

router.beforeEach((to) => {
  const store = useAppStore()
  const needAuth = to.matched.some((r) => r.meta?.requiresAuth)
  if (needAuth && !store.token) {
    return '/login'
  }
  if (to.path === '/app') {
    return roleHomePath(store.roleId)
  }
  if (to.path === '/notice/mine') {
    return roleNoticePath(store.roleId)
  }
  if (to.path === '/school') {
    return roleSchoolPath(store.roleId)
  }
  const roleGuard = to.matched.map((r) => r.meta?.roles).find((v) => Array.isArray(v) && v.length > 0)
  if (needAuth && roleGuard && !roleGuard.includes(store.roleId)) {
    return roleHomePath(store.roleId)
  }
  return true
})

export default router
