<template>
  <div class="page">
    <div class="card">
      <div class="title">{{ title }}</div>
      <div
        v-if="
          !isProfilePage &&
          !isEditPage &&
          !isAcademicPage &&
          !isTeacherInfoPage &&
          !isTeacherInfoEditPage &&
          !isTeacherInfoCreatePage &&
          !isAcademicEditPage &&
          !isAcademicCreatePage &&
          !isSecurityPage &&
          !isMentorPage &&
          !isMaterialPage
        "
        class="desc"
      >
        暂无内容
      </div>
      <div v-else class="content">
        <el-skeleton :loading="loading" animated>
          <template #template>
            <el-skeleton-item variant="h1" style="width: 180px" />
            <el-skeleton-item variant="text" style="margin-top: 12px" />
            <el-skeleton-item variant="text" style="margin-top: 8px" />
            <el-skeleton-item variant="text" style="margin-top: 8px" />
          </template>
          <template #default>
            <div :class="['wrap', { 'wrap-wide': isMaterialPage }]">
              <div
                v-if="
                  !isMentorPage &&
                  !isMaterialPage &&
                  !isAcademicPage &&
                  !isTeacherInfoPage &&
                  !isTeacherInfoEditPage &&
                  !isTeacherInfoCreatePage &&
                  !isAcademicEditPage &&
                  !isAcademicCreatePage &&
                  !isSecurityPage
                "
                class="top"
              >
                <el-upload
                  v-if="isEditPage"
                  class="avatar-uploader"
                  :action="uploadAction"
                  :headers="uploadHeaders"
                  :show-file-list="false"
                  :before-upload="beforeUpload"
                  :on-success="onUploadSuccess"
                >
                  <div class="avatar-upload-wrap">
                    <div class="avatar-click-area">
                      <el-avatar :size="76" :src="editAvatarUrl">{{ avatarFallback }}</el-avatar>
                      <div class="avatar-overlay">更换头像</div>
                    </div>
                    <div class="avatar-tip">点击头像上传</div>
                  </div>
                </el-upload>
                <el-avatar v-else :size="76" :src="topAvatarUrl">{{ avatarFallback }}</el-avatar>
                <div class="top-right">
                  <div class="name">{{ topDisplayName || '-' }}</div>
                  <div class="sub">{{ roleLabel }}</div>
                </div>
              </div>

              <div v-if="isAcademicPage" class="academic">
                <div class="academic-school">
                  <div class="academic-school-k">学校</div>
                  <div class="academic-school-v">{{ student.universityName || '-' }}</div>
                </div>

                <div class="grid">
                <div class="row">
                  <div class="label">学号：</div>
                  <div class="value">{{ student.studentNo || '-' }}</div>
                </div>
                <div class="row">
                  <div class="label">入学年份：</div>
                  <div class="value">{{ student.entryYear ? String(student.entryYear) : '-' }}</div>
                </div>
                <div class="row">
                  <div class="label">学院：</div>
                  <div class="value">{{ student.collegeName || '-' }}</div>
                </div>

                <div class="row">
                  <div class="label">专业：</div>
                  <div class="value">{{ student.majorName || '-' }}</div>
                </div>
                <div class="row">
                  <div class="label">班级：</div>
                  <div class="value">{{ student.className || '-' }}</div>
                </div>
                <div class="row">
                  <div class="label">绑定状态：</div>
                  <div class="value">{{ bindStatusLabel }}</div>
                </div>
                </div>
              </div>
              <div v-else-if="isTeacherInfoPage" class="teacher-info">
                <div class="academic-school">
                  <div class="academic-school-k">学校</div>
                  <div class="academic-school-v">{{ teacherSelf?.universityName || '-' }}</div>
                </div>

                <div class="grid">
                  <div class="row">
                    <div class="label">工号：</div>
                    <div class="value">{{ teacherSelf?.teacherNo || '-' }}</div>
                  </div>
                  <div class="row">
                    <div class="label">职称：</div>
                    <div class="value">{{ teacherSelf?.title || '-' }}</div>
                  </div>
                  <div class="row">
                    <div class="label">院系：</div>
                    <div class="value">{{ teacherSelf?.deptName || '-' }}</div>
                  </div>
                  <div class="row">
                    <div class="label">邮箱：</div>
                    <div class="value">{{ teacherSelf?.email || '-' }}</div>
                  </div>
                  <div class="row">
                    <div class="label">手机号：</div>
                    <div class="value">{{ teacherSelf?.phone || '-' }}</div>
                  </div>
                  <div class="row">
                    <div class="label">研究领域：</div>
                    <div class="value">{{ teacherSelf?.researchField || '-' }}</div>
                  </div>
                </div>
              </div>
              <div class="grid" v-else-if="isTeacherInfoEditPage || isTeacherInfoCreatePage">
                <div class="row">
                  <div class="label">学校：</div>
                  <div class="value-input">
                    <el-select
                      v-model="teacherInfoForm.universityId"
                      filterable
                      remote
                      reserve-keyword
                      :remote-method="searchUniversities"
                      :loading="universityLoading"
                      placeholder="输入学校名称搜索"
                      style="width: 100%"
                      @change="onTeacherUniversityChange"
                    >
                      <el-option v-for="u in universities" :key="u.id" :label="u.name" :value="u.id" />
                    </el-select>
                  </div>
                </div>
                <div class="row">
                  <div class="label">院系：</div>
                  <div class="value-input">
                    <el-select
                      v-model="teacherInfoForm.deptId"
                      filterable
                      placeholder="请选择院系"
                      style="width: 100%"
                      :disabled="!teacherInfoForm.universityId"
                      :loading="collegeLoading"
                    >
                      <el-option v-for="c in colleges" :key="c.id" :label="c.name" :value="c.id" />
                    </el-select>
                  </div>
                </div>
                <div class="row">
                  <div class="label">职称：</div>
                  <div class="value-input">
                    <el-input v-model="teacherInfoForm.title" placeholder="请输入职称" />
                  </div>
                </div>
                <div class="row">
                  <div class="label">工号：</div>
                  <div class="value-input">
                    <el-input v-model="teacherInfoForm.teacherNo" placeholder="请输入工号" />
                  </div>
                </div>
                <div class="row row-span">
                  <div class="label">研究领域：</div>
                  <div class="value-input">
                    <el-input v-model="teacherInfoForm.researchField" type="textarea" :rows="4" resize="none" placeholder="请输入研究领域/方向" />
                  </div>
                </div>
              </div>
              <div class="grid" v-else-if="isAcademicEditPage || isAcademicCreatePage">
                <div class="row">
                  <div class="label">学号：</div>
                  <div class="value-input">
                    <el-input v-model="academicForm.studentNo" placeholder="请输入学号" />
                  </div>
                </div>
                <div class="row">
                  <div class="label">入学年份：</div>
                  <div class="value-input">
                    <el-input-number v-model="academicForm.entryYear" :min="1900" :max="2100" controls-position="right" style="width: 100%" />
                  </div>
                </div>

                <div class="row">
                  <div class="label">学校：</div>
                  <div class="value-input">
                    <el-select
                      v-model="academicForm.universityId"
                      filterable
                      remote
                      reserve-keyword
                      :remote-method="searchUniversities"
                      :loading="universityLoading"
                      placeholder="输入学校名称搜索"
                      style="width: 100%"
                      @change="onUniversityChange"
                    >
                      <el-option v-for="u in universities" :key="u.id" :label="u.name" :value="u.id" />
                    </el-select>
                  </div>
                </div>
                <div class="row">
                  <div class="label">学院：</div>
                  <div class="value-input">
                    <el-select
                      v-model="academicForm.collegeId"
                      filterable
                      placeholder="请选择学院"
                      style="width: 100%"
                      :disabled="!academicForm.universityId"
                      :loading="collegeLoading"
                      @change="onCollegeChange"
                    >
                      <el-option v-for="c in colleges" :key="c.id" :label="c.name" :value="c.id" />
                    </el-select>
                  </div>
                </div>

                <div class="row">
                  <div class="label">专业：</div>
                  <div class="value-input">
                    <el-select
                      v-model="academicForm.majorId"
                      filterable
                      placeholder="请选择专业"
                      style="width: 100%"
                      :disabled="!academicForm.collegeId"
                      :loading="majorLoading"
                      @change="onMajorChange"
                    >
                      <el-option v-for="m in majors" :key="m.id" :label="m.name" :value="m.id" />
                    </el-select>
                  </div>
                </div>
                <div class="row">
                  <div class="label">班级：</div>
                  <div class="value-input">
                    <el-select
                      v-model="academicForm.classId"
                      filterable
                      placeholder="请选择班级"
                      style="width: 100%"
                      :disabled="!academicForm.majorId"
                      :loading="classLoading"
                    >
                      <el-option v-for="cl in classes" :key="cl.id" :label="cl.name" :value="cl.id" />
                    </el-select>
                  </div>
                </div>
              </div>

              <div class="mentor" v-else-if="isMentorPage">
                <div v-if="!teacher" class="mentor-empty">暂无导师信息</div>
                <div v-else class="mentor-wrap">
                  <div class="mentor-top">
                    <el-avatar :size="76" :src="mentorAvatarUrl">{{ mentorAvatarFallback }}</el-avatar>
                    <div class="mentor-top-right">
                      <div class="mentor-name">{{ teacher.realName || '-' }}</div>
                      <div class="mentor-sub">{{ teacher.title || '-' }}</div>
                    </div>
                  </div>
                  <div class="grid">
                    <div class="row">
                      <div class="label">工号：</div>
                      <div class="value">{{ teacher.teacherNo || '-' }}</div>
                    </div>
                    <div class="row">
                      <div class="label">性别：</div>
                      <div class="value">{{ mentorGenderLabel }}</div>
                    </div>
                    <div class="row">
                      <div class="label">学校：</div>
                      <div class="value">{{ teacher.universityName || '-' }}</div>
                    </div>
                    <div class="row">
                      <div class="label">学院：</div>
                      <div class="value">{{ teacher.deptName || '-' }}</div>
                    </div>
                    <div class="row">
                      <div class="label">邮箱：</div>
                      <div class="value">{{ teacher.email || '-' }}</div>
                    </div>
                    <div class="row">
                      <div class="label">手机号：</div>
                      <div class="value">{{ teacher.phone || '-' }}</div>
                    </div>
                    <div class="row">
                      <div class="label">研究领域：</div>
                      <div class="value">{{ teacher.researchField || '-' }}</div>
                    </div>
                  </div>
                  <div class="mentor-actions">
                    <div
                      class="action-tile"
                      role="button"
                      tabindex="0"
                      @click="goMessage"
                      @keydown.enter.prevent="goMessage"
                      @keydown.space.prevent="goMessage"
                    >
                      <div class="action-tile-left">
                        <div class="action-tile-title">联系导师</div>
                        <div class="action-tile-sub">点击进入留言信息，向导师发送消息</div>
                      </div>
                      <div class="action-tile-arrow">→</div>
                    </div>
                  </div>
                </div>
              </div>

              <div class="materials" v-else-if="isMaterialPage">
                <div class="materials-bar">
                  <div class="materials-bar-left">
                    <el-input v-model="materialQuery.title" clearable placeholder="请输入关键字" style="width: 260px" @keyup.enter="materialSearch" />
                    <el-select v-model="materialQuery.materialType" clearable placeholder="材料类型" style="width: 200px">
                      <el-option :value="1" label="学习计划" />
                      <el-option :value="2" label="进度汇报" />
                      <el-option :value="3" label="自我总结" />
                    </el-select>
                    <div class="materials-bar-actions">
                      <el-button type="primary" :loading="materialLoading" @click="materialSearch">搜索</el-button>
                      <el-button :disabled="materialLoading" @click="resetMaterialFilters">重置</el-button>
                    </div>
                  </div>
                  <div class="materials-bar-right">
                    <el-button type="primary" @click="goMaterialCreate">添加</el-button>
                  </div>
                </div>

                <div class="materials-table-wrap">
                  <el-table :data="materialRecords" style="width: 100%" :empty-text="materialLoading ? '加载中...' : '暂无材料'" v-loading="materialLoading">
                    <el-table-column prop="title" label="标题" min-width="220">
                      <template #default="{ row }">
                        <div class="materials-title">{{ row?.title || '-' }}</div>
                      </template>
                    </el-table-column>
                    <el-table-column prop="materialType" label="材料类型" width="120">
                      <template #default="{ row }">
                        {{ materialTypeLabel(row?.materialType) }}
                      </template>
                    </el-table-column>
                    <el-table-column prop="evaluated" label="批阅状态" width="110">
                      <template #default="{ row }">
                        <el-tag :type="row?.evaluated === 1 ? 'success' : 'info'">{{ evaluatedLabel(row?.evaluated) }}</el-tag>
                      </template>
                    </el-table-column>
                    <el-table-column prop="score" label="得分" width="90">
                      <template #default="{ row }">
                        {{ scoreLabel(row?.score) }}
                      </template>
                    </el-table-column>
                    <el-table-column prop="submitTime" label="提交时间" width="180">
                      <template #default="{ row }">
                        {{ row?.submitTime || '-' }}
                      </template>
                    </el-table-column>
                    <el-table-column prop="evaluationTime" label="批阅时间" width="180">
                      <template #default="{ row }">
                        {{ row?.evaluationTime || '-' }}
                      </template>
                    </el-table-column>
                    <el-table-column label="操作" width="180" fixed="right">
                      <template #default="{ row }">
                        <el-button type="primary" link @click="goMaterialDetail(row)">查看</el-button>
                        <el-button link @click="goMaterialEdit(row)">编辑</el-button>
                        <el-button type="danger" link :disabled="materialLoading || materialDeleting" @click="deleteMaterial(row)">删除</el-button>
                      </template>
                    </el-table-column>
                  </el-table>
                </div>

                <div class="materials-pager">
                  <el-pagination
                    v-model:current-page="materialQuery.page"
                    v-model:page-size="materialQuery.pageSize"
                    :page-sizes="[10, 20, 50]"
                    layout="total, sizes, prev, pager, next, jumper"
                    :total="materialTotal"
                    :disabled="materialLoading"
                    @current-change="fetchMaterials"
                    @size-change="onMaterialSizeChange"
                  />
                </div>
              </div>

              <div class="security" v-else-if="isSecurityPage">
              <div class="security-section">
                <div class="security-title">修改密码</div>
                <div class="grid">
                  <div class="row">
                    <div class="label">旧密码：</div>
                    <div class="value-input">
                      <el-input v-model="passwordForm.oldPassword" type="password" show-password placeholder="请输入旧密码" />
                    </div>
                  </div>
                  <div class="row">
                    <div class="label">新密码：</div>
                    <div class="value-input">
                      <el-input v-model="passwordForm.newPassword" type="password" show-password placeholder="请输入新密码" />
                    </div>
                  </div>
                </div>
                <div class="security-actions">
                  <div
                    :class="['action-tile', 'no-arrow', { disabled: passwordSaving }]"
                    role="button"
                    tabindex="0"
                    @click="!passwordSaving && submitPasswordChange()"
                    @keydown.enter.prevent="!passwordSaving && submitPasswordChange()"
                    @keydown.space.prevent="!passwordSaving && submitPasswordChange()"
                  >
                    <div class="action-tile-left">
                      <div class="action-tile-title">修改密码</div>
                      <div class="action-tile-sub">确认无误后提交，修改后需要重新登录</div>
                    </div>
                  </div>
                </div>
              </div>

              <div class="security-divider"></div>

              <div class="security-section">
                <div class="security-title danger">注销用户</div>
                <div class="security-desc">注销后账号将无法继续使用，请谨慎操作。</div>
                <div class="security-actions">
                  <div
                    :class="['action-tile', 'danger', 'no-arrow', { disabled: deletingAccount }]"
                    role="button"
                    tabindex="0"
                    @click="!deletingAccount && deleteAccount()"
                    @keydown.enter.prevent="!deletingAccount && deleteAccount()"
                    @keydown.space.prevent="!deletingAccount && deleteAccount()"
                  >
                    <div class="action-tile-left">
                      <div class="action-tile-title">注销用户</div>
                      <div class="action-tile-sub">此操作不可恢复，请谨慎确认</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

              <div class="grid" v-else>
                <div class="row">
                  <div class="label">真实姓名：</div>
                  <div v-if="isEditPage" class="value-input">
                    <el-input v-model="editForm.realName" placeholder="请输入真实姓名" />
                  </div>
                  <div v-else class="value">{{ info.realName || '-' }}</div>
                </div>
                <div class="row" v-if="!isEditPage">
                  <div class="label">用户名：</div>
                  <div class="value">{{ info.username || '-' }}</div>
                </div>

                <div class="row" v-if="!isEditPage">
                  <div class="label">手机号：</div>
                  <div class="value">{{ info.phone || '-' }}</div>
                </div>
                <div class="row">
                  <div class="label">邮箱：</div>
                  <div v-if="isEditPage" class="value-input">
                    <el-input v-model="editForm.email" placeholder="请输入邮箱" />
                  </div>
                  <div v-else class="value">{{ info.email || '-' }}</div>
                </div>

                <div class="row">
                  <div class="label">出生年月：</div>
                  <div v-if="isEditPage" class="value-input">
                    <el-date-picker
                      v-model="editForm.birthday"
                      type="date"
                      placeholder="请选择日期"
                      style="width: 100%"
                      value-format="YYYY-MM-DD"
                    />
                  </div>
                  <div v-else class="value">{{ info.birthday || '-' }}</div>
                </div>
                <div class="row">
                  <div class="label">性别：</div>
                  <div v-if="isEditPage" class="value-input">
                    <el-radio-group v-model="editForm.gender">
                      <el-radio :value="0">保密</el-radio>
                      <el-radio :value="1">男</el-radio>
                      <el-radio :value="2">女</el-radio>
                    </el-radio-group>
                  </div>
                  <div v-else class="value">{{ genderLabel }}</div>
                </div>

                <div class="row" v-if="!isEditPage">
                  <div class="label">注册时间：</div>
                  <div class="value">{{ info.createTime || '-' }}</div>
                </div>
              </div>

              <div
                class="actions"
                v-if="
                  isProfilePage ||
                  isEditPage ||
                  isAcademicPage ||
                  isAcademicEditPage ||
                  isAcademicCreatePage ||
                  isTeacherInfoPage ||
                  isTeacherInfoEditPage ||
                  isTeacherInfoCreatePage
                "
              >
                <div
                  v-if="isProfilePage"
                  class="action-tile"
                  role="button"
                  tabindex="0"
                  @click="goEdit"
                  @keydown.enter.prevent="goEdit"
                  @keydown.space.prevent="goEdit"
                >
                  <div class="action-tile-left">
                    <div class="action-tile-title">修改信息</div>
                    <div class="action-tile-sub">完善个人资料，更新邮箱、生日等</div>
                  </div>
                  <div class="action-tile-arrow">→</div>
                </div>
                <template v-else-if="isEditPage">
                  <el-button type="primary" :loading="saving" @click="saveEdit">保存</el-button>
                  <el-button :disabled="saving" @click="cancelEdit">取消</el-button>
                </template>
                <div
                  v-else-if="isAcademicPage"
                  class="action-tile"
                  role="button"
                  tabindex="0"
                  @click="goAcademicEdit"
                  @keydown.enter.prevent="goAcademicEdit"
                  @keydown.space.prevent="goAcademicEdit"
                >
                  <div class="action-tile-left">
                    <div class="action-tile-title">修改学籍信息</div>
                    <div class="action-tile-sub">更新学校、学院、专业、班级等信息</div>
                  </div>
                  <div class="action-tile-arrow">→</div>
                </div>
                <template v-else-if="isAcademicEditPage">
                  <el-button type="primary" :loading="academicSaving" @click="saveAcademicEdit">保存</el-button>
                  <el-button :disabled="academicSaving" @click="cancelAcademicEdit">取消</el-button>
                </template>
                <template v-else-if="isAcademicCreatePage">
                  <el-button type="primary" :loading="academicSaving" @click="saveAcademicCreate">保存</el-button>
                  <el-button :disabled="academicSaving" @click="cancelAcademicCreate">取消</el-button>
                </template>
                <div
                  v-else-if="isTeacherInfoPage"
                  class="action-tile"
                  role="button"
                  tabindex="0"
                  @click="goTeacherInfoEdit"
                  @keydown.enter.prevent="goTeacherInfoEdit"
                  @keydown.space.prevent="goTeacherInfoEdit"
                >
                  <div class="action-tile-left">
                    <div class="action-tile-title">修改导师信息</div>
                    <div class="action-tile-sub">更新学校、院系、研究方向、职称等信息</div>
                  </div>
                  <div class="action-tile-arrow">→</div>
                </div>
                <template v-else-if="isTeacherInfoEditPage">
                  <el-button type="primary" :loading="teacherInfoSaving" @click="saveTeacherInfoEdit">保存</el-button>
                  <el-button :disabled="teacherInfoSaving" @click="cancelTeacherInfoEdit">取消</el-button>
                </template>
                <template v-else-if="isTeacherInfoCreatePage">
                  <el-button type="primary" :loading="teacherInfoSaving" @click="saveTeacherInfoCreate">保存</el-button>
                  <el-button :disabled="teacherInfoSaving" @click="cancelTeacherInfoCreate">取消</el-button>
                </template>
              </div>
            </div>
          </template>
        </el-skeleton>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import http from '../api/http'
import { useAppStore } from '../store'
import { ElMessage, ElMessageBox } from 'element-plus'

const route = useRoute()
const router = useRouter()
const store = useAppStore()
const title = computed(() => route.meta?.title || '我的信息')
const isProfilePage = computed(() => route.meta?.title === '个人信息')
const isAcademicPage = computed(() => route.meta?.title === '学籍信息')
const isTeacherInfoPage = computed(() => route.meta?.title === '导师信息')
const isEditPage = computed(() => route.meta?.mode === 'edit')
const isAcademicEditPage = computed(() => route.meta?.mode === 'academic-edit')
const isAcademicCreatePage = computed(() => route.meta?.mode === 'academic-create')
const isTeacherInfoEditPage = computed(() => route.meta?.mode === 'teacher-edit')
const isTeacherInfoCreatePage = computed(() => route.meta?.mode === 'teacher-create')
const isSecurityPage = computed(() => route.meta?.title === '安全信息')
const isMentorPage = computed(() => route.meta?.title === '我的导师')
const isMaterialPage = computed(() => route.meta?.title === '我的材料')

const loading = ref(false)
const materialLoading = ref(false)
const materialDeleting = ref(false)
const saving = ref(false)
const academicSaving = ref(false)
const info = ref({
  avatar: '',
  birthday: '',
  createTime: '',
  email: '',
  gender: 0,
  id: 0,
  phone: '',
  realName: '',
  roleId: 0,
  username: ''
})

const roleLabel = computed(() => {
  if ((info.value.roleId || store.roleId) === 1) return '管理员端'
  if ((info.value.roleId || store.roleId) === 2) return '导师端'
  return '学生端'
})
const genderLabel = computed(() => {
  const g = info.value.gender
  if (g === 1) return '男'
  if (g === 2) return '女'
  return '保密'
})
function normalizeUrl(a) {
  if (!a) return ''
  if (/^https?:\/\//i.test(a)) return a
  if (a.startsWith('/')) return a
  return a
}

const topDisplayName = computed(() => {
  if (isAcademicPage.value || isAcademicEditPage.value || isAcademicCreatePage.value) {
    return student.value.realName || info.value.realName || store.realName || store.userName || ''
  }
  if (isEditPage.value) return editForm.value.realName || info.value.realName || store.realName || store.userName || ''
  return info.value.realName || store.realName || store.userName || ''
})

const topAvatarUrl = computed(() => {
  if (isAcademicPage.value || isAcademicEditPage.value || isAcademicCreatePage.value) return normalizeUrl(student.value.avatar || store.avatar)
  return normalizeUrl(info.value.avatar || store.avatar)
})

const avatarFallback = computed(() => topDisplayName.value.trim().slice(0, 1))

const student = ref({
  avatar: '',
  bindStatus: 0,
  classId: 0,
  className: '',
  collegeId: 0,
  collegeName: '',
  entryYear: 0,
  gender: 0,
  id: 0,
  majorId: 0,
  majorName: '',
  realName: '',
  studentNo: '',
  universityId: 0,
  universityName: ''
})

const teacher = ref(null)
const mentorGenderLabel = computed(() => {
  const g = teacher.value?.gender
  if (g === 1) return '男'
  if (g === 2) return '女'
  return '保密'
})
const mentorAvatarUrl = computed(() => normalizeUrl(teacher.value?.avatar || ''))
const mentorAvatarFallback = computed(() => (teacher.value?.realName || '').trim().slice(0, 1))

const teacherSelf = ref(null)
const teacherInfoForm = ref({
  deptId: undefined,
  researchField: '',
  teacherNo: '',
  title: '',
  universityId: undefined
})
const teacherInfoSaving = ref(false)

const materialQuery = ref({
  materialType: undefined,
  page: 1,
  pageSize: 10,
  title: ''
})
const materialTotal = ref(0)
const materialRecords = ref([])

const studentGenderLabel = computed(() => {
  const g = student.value.gender
  if (g === 1) return '男'
  if (g === 2) return '女'
  return '保密'
})

const bindStatusLabel = computed(() => {
  const s = student.value.bindStatus
  if (s === 1) return '已绑定导师'
  if (s === 0) return '未绑定导师'
  return '-'
})

const editForm = ref({
  avatar: '',
  birthday: '',
  email: '',
  gender: 0,
  realName: ''
})

const uploadAction = computed(() => '/user/common/upload')
const uploadHeaders = computed(() => ({ token: store.token || '' }))
const editAvatarUrl = computed(() => {
  return normalizeUrl(editForm.value.avatar || topAvatarUrl.value)
})

const academicForm = ref({
  classId: undefined,
  collegeId: undefined,
  entryYear: undefined,
  majorId: undefined,
  studentNo: '',
  universityId: undefined
})

const universityLoading = ref(false)
const collegeLoading = ref(false)
const majorLoading = ref(false)
const classLoading = ref(false)
const universities = ref([])
const colleges = ref([])
const majors = ref([])
const classes = ref([])

const passwordForm = ref({
  oldPassword: '',
  newPassword: ''
})
const passwordSaving = ref(false)
const deletingAccount = ref(false)

async function fetchInfo() {
  loading.value = true
  try {
    const { data } = await http.post('/user/info')
    info.value = data?.data || info.value
    store.setUser({
      ...(store.user || {}),
      ...info.value,
      userName: info.value.username || store.user?.userName || store.userName
    })
    if (isEditPage.value) {
      editForm.value = {
        avatar: info.value.avatar || '',
        birthday: info.value.birthday || '',
        email: info.value.email || '',
        gender: info.value.gender ?? 0,
        realName: info.value.realName || ''
      }
    }
  } catch (_) {
    return
  } finally {
    loading.value = false
  }
}

async function fetchStudent() {
  loading.value = true
  try {
    const { data } = await http.get('/student')
    const hasInfo = data?.data !== null && data?.data !== undefined
    if (hasInfo) {
      student.value = data?.data || student.value
      if (isAcademicCreatePage.value) {
        router.replace(`${roleBase.value}/me/academic`)
      }
      return
    }
    if (isAcademicPage.value || isAcademicEditPage.value) {
      router.replace(`${roleBase.value}/me/academic/create`)
    }
  } catch (_) {
    return
  } finally {
    loading.value = false
  }
}

async function fetchTeacher() {
  loading.value = true
  try {
    const { data } = await http.get('/student/teacher')
    teacher.value = data?.data || null
  } catch (_) {
    return
  } finally {
    loading.value = false
  }
}

async function fetchTeacherSelf() {
  loading.value = true
  try {
    const { data } = await http.get('/teacher')
    teacherSelf.value = data?.data || null
  } catch (_) {
    return
  } finally {
    loading.value = false
  }
}

function materialTypeLabel(t) {
  if (t === 1) return '学习计划'
  if (t === 2) return '进度汇报'
  if (t === 3) return '自我总结'
  return t === 0 ? '0' : t ? String(t) : '-'
}

function evaluatedLabel(v) {
  return v === 1 ? '已批阅' : '未批阅'
}

function scoreLabel(v) {
  if (v === 0) return '0'
  return v === undefined || v === null || v === '' ? '-' : String(v)
}

async function fetchMaterials(toPage = materialQuery.value.page) {
  const page = Number(toPage)
  materialQuery.value.page = Number.isFinite(page) && page > 0 ? page : 1
  const params = {
    materialType: materialQuery.value.materialType ?? undefined,
    page: materialQuery.value.page,
    pageSize: materialQuery.value.pageSize,
    title: (materialQuery.value.title || '').trim() || undefined
  }
  materialLoading.value = true
  try {
    syncMaterialListQueryToRoute()
    const { data } = await http.get('/student/material/page', { params })
    const pageData = data?.data || {}
    materialTotal.value = pageData?.total ?? 0
    materialRecords.value = Array.isArray(pageData?.records) ? pageData.records : []
  } catch (_) {
    return
  } finally {
    materialLoading.value = false
  }
}

function parseQueryNumber(v) {
  const n = Number(v)
  return Number.isFinite(n) ? n : undefined
}

function applyMaterialListQueryFromRoute() {
  const q = route.query || {}
  const page = parseQueryNumber(q.page)
  const pageSize = parseQueryNumber(q.pageSize)
  const materialType = parseQueryNumber(q.materialType)
  const title = typeof q.title === 'string' ? q.title : ''
  materialQuery.value.page = page && page > 0 ? page : 1
  materialQuery.value.pageSize = pageSize && pageSize > 0 ? pageSize : materialQuery.value.pageSize || 10
  materialQuery.value.materialType = materialType && materialType > 0 ? materialType : undefined
  materialQuery.value.title = title || ''
}

function getMaterialListQuery() {
  const q = {}
  if (materialQuery.value.page && Number(materialQuery.value.page) > 1) q.page = String(materialQuery.value.page)
  if (materialQuery.value.pageSize && Number(materialQuery.value.pageSize) !== 10) q.pageSize = String(materialQuery.value.pageSize)
  if (materialQuery.value.materialType) q.materialType = String(materialQuery.value.materialType)
  const title = (materialQuery.value.title || '').trim()
  if (title) q.title = title
  return q
}

function syncMaterialListQueryToRoute() {
  if (!isMaterialPage.value) return
  const next = getMaterialListQuery()
  const curr = route.query || {}
  const same =
    String(curr.page || '') === String(next.page || '') &&
    String(curr.pageSize || '') === String(next.pageSize || '') &&
    String(curr.materialType || '') === String(next.materialType || '') &&
    String(curr.title || '') === String(next.title || '')
  if (same) return
  router.replace({ path: route.path, query: next })
}

function materialSearch() {
  if (materialLoading.value) return
  fetchMaterials(1)
}

function resetMaterialFilters() {
  materialQuery.value = { materialType: undefined, page: 1, pageSize: materialQuery.value.pageSize || 10, title: '' }
  fetchMaterials(1)
}

function onMaterialSizeChange(size) {
  materialQuery.value.pageSize = size
  fetchMaterials(1)
}

function goMaterialDetail(row) {
  const id = row?.id
  if (!id) return
  router.push({ path: `${roleBase.value}/my-material/${id}`, query: getMaterialListQuery() })
}

function goMaterialCreate() {
  router.push({ path: `${roleBase.value}/my-material/create`, query: getMaterialListQuery() })
}

function goMaterialEdit(row) {
  const id = row?.id
  if (!id) return
  router.push({ path: `${roleBase.value}/my-material/${id}/edit`, query: getMaterialListQuery() })
}

function goMessage() {
  const userId = teacher.value?.userId
  const targetPath = roleBase.value === '/teacher' ? '/teacher/messages' : '/student/message'
  if (userId) {
    router.push({ 
      path: targetPath, 
      query: { 
        contactId: userId, 
        contactName: teacher.value?.realName, 
        contactRole: 2, 
        contactAvatar: teacher.value?.avatar || '' 
      } 
    })
  } else {
    router.push(targetPath)
  }
}

async function deleteMaterial(row) {
  const id = row?.id
  if (!id) return
  if (materialDeleting.value || materialLoading.value) return
  try {
    await ElMessageBox.confirm('确认删除该材料？此操作不可恢复。', '确认删除', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning'
    })
  } catch (_) {
    return
  }
  const shouldBackPage = materialRecords.value.length <= 1 && materialQuery.value.page > 1
  materialDeleting.value = true
  try {
    await http.delete(`/student/material/${id}`)
    ElMessage.success('删除成功')
    const nextPage = shouldBackPage ? materialQuery.value.page - 1 : materialQuery.value.page
    await fetchMaterials(nextPage)
  } finally {
    materialDeleting.value = false
  }
}

function normalizeId(v) {
  if (v === undefined || v === null || v === '') return undefined
  const n = Number(v)
  return Number.isFinite(n) ? n : v
}

function getName(x) {
  return x?.name ?? x?.universityName ?? x?.deptName ?? ''
}

function asArray(v) {
  if (Array.isArray(v)) return v
  if (Array.isArray(v?.records)) return v.records
  if (Array.isArray(v?.list)) return v.list
  if (Array.isArray(v?.items)) return v.items
  if (Array.isArray(v?.rows)) return v.rows
  return []
}

function seedOption(list, id, name) {
  const nid = normalizeId(id)
  const nname = (name || '').trim()
  if (!nid || !nname) return
  const exists = list.some((x) => String(x?.id) === String(nid))
  if (!exists) list.push({ id: nid, name: nname })
}

async function searchUniversities(query) {
  const q = (query || '').trim()
  if (!q) return
  universityLoading.value = true
  try {
    const { data } = await http.get('/school-hierarchy/universities/search', { params: { name: q } })
    const arr = asArray(data?.data)
    universities.value = arr.map((x) => ({ id: normalizeId(x?.id), name: getName(x) })).filter((x) => x.id && x.name)
  } finally {
    universityLoading.value = false
  }
}

async function loadColleges(universityId) {
  const id = normalizeId(universityId)
  if (!id) return
  collegeLoading.value = true
  try {
    const { data } = await http.get(`/school-hierarchy/universities/${id}/colleges`)
    const arr = asArray(data?.data)
    colleges.value = arr.map((x) => ({ id: normalizeId(x?.id), name: getName(x) })).filter((x) => x.id && x.name)
    if (String(id) === String(normalizeId(student.value.universityId))) {
      seedOption(colleges.value, student.value.collegeId, student.value.collegeName)
    }
  } finally {
    collegeLoading.value = false
  }
}

async function loadMajors(collegeId) {
  const id = normalizeId(collegeId)
  if (!id) return
  majorLoading.value = true
  try {
    const { data } = await http.get(`/school-hierarchy/colleges/${id}/majors`)
    const arr = asArray(data?.data)
    majors.value = arr.map((x) => ({ id: normalizeId(x?.id), name: getName(x) })).filter((x) => x.id && x.name)
    if (String(id) === String(normalizeId(student.value.collegeId))) {
      seedOption(majors.value, student.value.majorId, student.value.majorName)
    }
  } finally {
    majorLoading.value = false
  }
}

async function loadClasses(majorId) {
  const id = normalizeId(majorId)
  if (!id) return
  classLoading.value = true
  try {
    const { data } = await http.get(`/school-hierarchy/majors/${id}/classes`)
    const arr = asArray(data?.data)
    classes.value = arr.map((x) => ({ id: normalizeId(x?.id), name: getName(x) })).filter((x) => x.id && x.name)
    if (String(id) === String(normalizeId(student.value.majorId))) {
      seedOption(classes.value, student.value.classId, student.value.className)
    }
  } finally {
    classLoading.value = false
  }
}

async function initAcademicEdit() {
  academicForm.value = {
    classId: normalizeId(student.value.classId) || undefined,
    collegeId: normalizeId(student.value.collegeId) || undefined,
    entryYear: student.value.entryYear || undefined,
    majorId: normalizeId(student.value.majorId) || undefined,
    studentNo: student.value.studentNo ? String(student.value.studentNo) : '',
    universityId: normalizeId(student.value.universityId) || undefined
  }
  universities.value = []
  colleges.value = []
  majors.value = []
  classes.value = []
  seedOption(universities.value, student.value.universityId, student.value.universityName)
  seedOption(colleges.value, student.value.collegeId, student.value.collegeName)
  seedOption(majors.value, student.value.majorId, student.value.majorName)
  seedOption(classes.value, student.value.classId, student.value.className)
  if (academicForm.value.universityId) await loadColleges(academicForm.value.universityId)
  if (academicForm.value.collegeId) await loadMajors(academicForm.value.collegeId)
  if (academicForm.value.majorId) await loadClasses(academicForm.value.majorId)
}

function initAcademicCreate() {
  academicForm.value = {
    classId: undefined,
    collegeId: undefined,
    entryYear: undefined,
    majorId: undefined,
    studentNo: '',
    universityId: undefined
  }
  universities.value = []
  colleges.value = []
  majors.value = []
  classes.value = []
}

async function initTeacherInfoEdit() {
  teacherInfoForm.value = {
    deptId: normalizeId(teacherSelf.value?.deptId) || undefined,
    researchField: (teacherSelf.value?.researchField || '').trim(),
    teacherNo: teacherSelf.value?.teacherNo ? String(teacherSelf.value.teacherNo) : '',
    title: (teacherSelf.value?.title || '').trim(),
    universityId: normalizeId(teacherSelf.value?.universityId) || undefined
  }
  universities.value = []
  colleges.value = []
  majors.value = []
  classes.value = []
  seedOption(universities.value, teacherSelf.value?.universityId, teacherSelf.value?.universityName)
  if (teacherInfoForm.value.universityId) await loadColleges(teacherInfoForm.value.universityId)
  seedOption(colleges.value, teacherSelf.value?.deptId, teacherSelf.value?.deptName)
}

async function initTeacherInfoCreate() {
  teacherInfoForm.value = {
    deptId: normalizeId(teacherSelf.value?.deptId) || undefined,
    researchField: (teacherSelf.value?.researchField || '').trim(),
    teacherNo: teacherSelf.value?.teacherNo ? String(teacherSelf.value.teacherNo) : '',
    title: (teacherSelf.value?.title || '').trim(),
    universityId: normalizeId(teacherSelf.value?.universityId) || undefined
  }
  universities.value = []
  colleges.value = []
  majors.value = []
  classes.value = []
  seedOption(universities.value, teacherSelf.value?.universityId, teacherSelf.value?.universityName)
  if (teacherInfoForm.value.universityId) await loadColleges(teacherInfoForm.value.universityId)
  seedOption(colleges.value, teacherSelf.value?.deptId, teacherSelf.value?.deptName)
}

const roleBase = computed(() => {
  if (route.path.startsWith('/admin')) return '/admin'
  if (route.path.startsWith('/teacher')) return '/teacher'
  if (route.path.startsWith('/student')) return '/student'
  if (store.roleId === 1) return '/admin'
  if (store.roleId === 2) return '/teacher'
  return '/student'
})

function goEdit() {
  router.push(`${roleBase.value}/me/profile/edit`)
}

function cancelEdit() {
  router.push(`${roleBase.value}/me/profile`)
}

function goAcademicEdit() {
  router.push(`${roleBase.value}/me/academic/edit`)
}

function cancelAcademicEdit() {
  router.push(`${roleBase.value}/me/academic`)
}

function cancelAcademicCreate() {
  router.push(`${roleBase.value}/me/profile`)
}

function goTeacherInfoEdit() {
  router.push(`${roleBase.value}/me/teacher/edit`)
}

function cancelTeacherInfoEdit() {
  router.push(`${roleBase.value}/me/teacher`)
}

function cancelTeacherInfoCreate() {
  router.push(`${roleBase.value}/me/profile`)
}

function isTeacherInfoCompleted(v) {
  const teacherNo = (v?.teacherNo ? String(v.teacherNo) : '').trim()
  const titleVal = (v?.title || '').trim()
  const researchFieldVal = (v?.researchField || '').trim()
  const universityId = normalizeId(v?.universityId)
  const deptId = normalizeId(v?.deptId)
  return !!teacherNo && !!titleVal && !!researchFieldVal && !!universityId && !!deptId
}

async function loadTeacherInfoPage() {
  teacherSelf.value = null
  await fetchTeacherSelf()
  const ok = isTeacherInfoCompleted(teacherSelf.value)

  if (!ok) {
    if (!isTeacherInfoCreatePage.value) {
      router.replace(`${roleBase.value}/me/teacher/create`)
      return
    }
    await initTeacherInfoCreate()
    return
  }

  if (isTeacherInfoCreatePage.value) {
    router.replace(`${roleBase.value}/me/teacher`)
    return
  }

  if (isTeacherInfoEditPage.value) await initTeacherInfoEdit()
}

async function submitPasswordChange() {
  if (passwordSaving.value) return
  const oldPassword = (passwordForm.value.oldPassword || '').trim()
  const newPassword = (passwordForm.value.newPassword || '').trim()
  if (!oldPassword) {
    ElMessage.error('请输入旧密码')
    return
  }
  if (!newPassword) {
    ElMessage.error('请输入新密码')
    return
  }
  try {
    await ElMessageBox.confirm('确认修改密码？修改后需要重新登录。', '确认修改', {
      confirmButtonText: '确认',
      cancelButtonText: '取消',
      type: 'warning'
    })
  } catch (_) {
    return
  }
  passwordSaving.value = true
  try {
    const payload = {
      oldPassword,
      newPassword,
      passwordEditDTO: { oldPassword, newPassword }
    }
    await http.post('/user/editPassword', payload)
    ElMessage.success('密码修改成功，请重新登录')
    store.clearAuth()
    router.push('/login')
  } finally {
    passwordSaving.value = false
  }
}

async function deleteAccount() {
  try {
    await ElMessageBox.confirm('确认注销用户？此操作不可恢复。', '确认注销', {
      confirmButtonText: '确认',
      cancelButtonText: '取消',
      type: 'warning'
    })
  } catch (_) {
    return
  }
  deletingAccount.value = true
  try {
    await http.post('/user/deleteAccount')
    ElMessage.success('已注销账号')
    store.clearAuth()
    router.push('/login')
  } finally {
    deletingAccount.value = false
  }
}

async function onUniversityChange(universityId) {
  academicForm.value.collegeId = undefined
  academicForm.value.majorId = undefined
  academicForm.value.classId = undefined
  colleges.value = []
  majors.value = []
  classes.value = []
  if (universityId) await loadColleges(universityId)
}

async function onTeacherUniversityChange(universityId) {
  teacherInfoForm.value.deptId = undefined
  colleges.value = []
  if (universityId) await loadColleges(universityId)
}

async function onCollegeChange(collegeId) {
  academicForm.value.majorId = undefined
  academicForm.value.classId = undefined
  majors.value = []
  classes.value = []
  if (collegeId) await loadMajors(collegeId)
}

async function onMajorChange(majorId) {
  academicForm.value.classId = undefined
  classes.value = []
  if (majorId) await loadClasses(majorId)
}

async function saveAcademicEdit() {
  const payload = {
    classId: academicForm.value.classId,
    collegeId: academicForm.value.collegeId,
    entryYear: academicForm.value.entryYear,
    majorId: academicForm.value.majorId,
    studentNo: (academicForm.value.studentNo || '').trim(),
    universityId: academicForm.value.universityId
  }
  if (!payload.studentNo) {
    ElMessage.error('请输入学号')
    return
  }
  if (!payload.entryYear) {
    ElMessage.error('请输入入学年份')
    return
  }
  if (!payload.universityId) {
    ElMessage.error('请选择学校')
    return
  }
  if (!payload.collegeId) {
    ElMessage.error('请选择学院')
    return
  }
  if (!payload.majorId) {
    ElMessage.error('请选择专业')
    return
  }
  if (!payload.classId) {
    ElMessage.error('请选择班级')
    return
  }

  const universityChanged = String(normalizeId(payload.universityId)) !== String(normalizeId(student.value.universityId))
  const collegeChanged = String(normalizeId(payload.collegeId)) !== String(normalizeId(student.value.collegeId))
  const willUnbind = student.value.bindStatus === 1 && (universityChanged || collegeChanged)
  const msg = willUnbind
    ? '确认保存本次学籍信息修改？\n\n提示：修改学校或学院将导致当前导师绑定关系解除。'
    : '确认保存本次学籍信息修改？'
  try {
    await ElMessageBox.confirm(msg, '确认修改', {
      confirmButtonText: '确认',
      cancelButtonText: '取消',
      type: willUnbind ? 'warning' : 'info'
    })
  } catch (_) {
    return
  }

  academicSaving.value = true
  try {
    try {
      await http.put('/student', payload)
    } catch (e) {
      await http.put('/student', { studentInfoDTO: payload })
    }
    ElMessage.success('保存成功')
    await fetchStudent()
    router.push(`${roleBase.value}/me/academic`)
  } finally {
    academicSaving.value = false
  }
}

async function saveTeacherInfoEdit() {
  if (teacherInfoSaving.value) return
  const payload = {
    deptId: teacherInfoForm.value.deptId,
    researchField: (teacherInfoForm.value.researchField || '').trim(),
    teacherNo: (teacherInfoForm.value.teacherNo || '').trim(),
    title: (teacherInfoForm.value.title || '').trim(),
    universityId: teacherInfoForm.value.universityId
  }
  if (!payload.teacherNo) {
    ElMessage.error('请输入工号')
    return
  }
  if (!payload.title) {
    ElMessage.error('请输入职称')
    return
  }
  if (!payload.researchField) {
    ElMessage.error('请输入研究领域')
    return
  }
  if (!payload.universityId) {
    ElMessage.error('请选择学校')
    return
  }
  if (!payload.deptId) {
    ElMessage.error('请选择院系')
    return
  }
  teacherInfoSaving.value = true
  try {
    try {
      await http.put('/teacher', payload)
    } catch (e) {
      await http.put('/teacher', { teacherInfoDTO: payload })
    }
    ElMessage.success('保存成功')
    await fetchTeacherSelf()
    router.push(`${roleBase.value}/me/teacher`)
  } finally {
    teacherInfoSaving.value = false
  }
}

async function saveTeacherInfoCreate() {
  if (teacherInfoSaving.value) return
  const payload = {
    deptId: teacherInfoForm.value.deptId,
    researchField: (teacherInfoForm.value.researchField || '').trim(),
    teacherNo: (teacherInfoForm.value.teacherNo || '').trim(),
    title: (teacherInfoForm.value.title || '').trim(),
    universityId: teacherInfoForm.value.universityId
  }
  if (!payload.teacherNo) {
    ElMessage.error('请输入工号')
    return
  }
  if (!payload.title) {
    ElMessage.error('请输入职称')
    return
  }
  if (!payload.researchField) {
    ElMessage.error('请输入研究领域')
    return
  }
  if (!payload.universityId) {
    ElMessage.error('请选择学校')
    return
  }
  if (!payload.deptId) {
    ElMessage.error('请选择院系')
    return
  }
  teacherInfoSaving.value = true
  try {
    try {
      await http.post('/teacher', payload)
    } catch (e) {
      await http.post('/teacher', { teacherInfoDTO: payload })
    }
    ElMessage.success('保存成功')
    await fetchTeacherSelf()
    router.push(`${roleBase.value}/me/teacher`)
  } finally {
    teacherInfoSaving.value = false
  }
}

async function saveAcademicCreate() {
  const payload = {
    classId: academicForm.value.classId,
    collegeId: academicForm.value.collegeId,
    entryYear: academicForm.value.entryYear,
    majorId: academicForm.value.majorId,
    studentNo: (academicForm.value.studentNo || '').trim(),
    universityId: academicForm.value.universityId
  }
  if (!payload.studentNo) {
    ElMessage.error('请输入学号')
    return
  }
  if (!payload.entryYear) {
    ElMessage.error('请输入入学年份')
    return
  }
  if (!payload.universityId) {
    ElMessage.error('请选择学校')
    return
  }
  if (!payload.collegeId) {
    ElMessage.error('请选择学院')
    return
  }
  if (!payload.majorId) {
    ElMessage.error('请选择专业')
    return
  }
  if (!payload.classId) {
    ElMessage.error('请选择班级')
    return
  }

  try {
    await ElMessageBox.confirm('确认提交学籍信息？', '确认提交', {
      confirmButtonText: '确认',
      cancelButtonText: '取消',
      type: 'info'
    })
  } catch (_) {
    return
  }

  academicSaving.value = true
  try {
    try {
      await http.post('/student', payload)
    } catch (e) {
      await http.post('/student', { studentInfoDTO: payload })
    }
    ElMessage.success('保存成功')
    router.push(`${roleBase.value}/me/academic`)
  } finally {
    academicSaving.value = false
  }
}

function beforeUpload(file) {
  const okType = (file?.type || '').startsWith('image/')
  const okSize = (file?.size || 0) / 1024 / 1024 <= 2
  if (!okType) ElMessage.error('只支持上传图片')
  if (!okSize) ElMessage.error('图片大小不能超过2MB')
  return okType && okSize
}

function onUploadSuccess(resp) {
  if (resp?.code === 1 && resp?.data) {
    editForm.value.avatar = resp.data
    return
  }
  ElMessage.error(resp?.msg || '上传失败')
}

async function saveEdit() {
  saving.value = true
  try {
    const payload = {
      avatar: editForm.value.avatar || '',
      birthday: editForm.value.birthday || '',
      email: editForm.value.email || '',
      gender: editForm.value.gender ?? 0,
      realName: editForm.value.realName || ''
    }
    await http.post('/user/update', payload)
    ElMessage.success('保存成功')
    await fetchInfo()
    router.push(`${roleBase.value}/me/profile`)
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  if (isMentorPage.value) {
    fetchTeacher()
    return
  }
  if (isMaterialPage.value) {
    applyMaterialListQueryFromRoute()
    fetchMaterials()
    return
  }
  if (isTeacherInfoPage.value || isTeacherInfoEditPage.value || isTeacherInfoCreatePage.value) {
    loadTeacherInfoPage()
    return
  }
  if (isAcademicPage.value || isAcademicEditPage.value || isAcademicCreatePage.value) {
    fetchStudent().then(() => {
      if (isAcademicEditPage.value) initAcademicEdit()
      if (isAcademicCreatePage.value) initAcademicCreate()
    })
    return
  }
  if (title.value === '个人信息' || isEditPage.value) fetchInfo()
})

watch(title, (t) => {
  if (t === '我的导师') {
    teacher.value = null
    fetchTeacher()
    return
  }
  if (t === '我的材料') {
    materialRecords.value = []
    materialTotal.value = 0
    applyMaterialListQueryFromRoute()
    fetchMaterials()
    return
  }
  if (t === '导师信息' || t === '修改导师信息' || t === '完善导师信息') {
    loadTeacherInfoPage()
    return
  }
  if (t === '学籍信息' || isAcademicEditPage.value || isAcademicCreatePage.value) {
    fetchStudent().then(() => {
      if (isAcademicEditPage.value) initAcademicEdit()
      if (isAcademicCreatePage.value) initAcademicCreate()
    })
    return
  }
  if (t === '安全信息') {
    passwordForm.value = { oldPassword: '', newPassword: '' }
    return
  }
  if (t === '个人信息' || isEditPage.value) fetchInfo()
})

watch(isEditPage, (editing) => {
  if (editing) {
    editForm.value = {
      avatar: info.value.avatar || '',
      birthday: info.value.birthday || '',
      email: info.value.email || '',
      gender: info.value.gender ?? 0,
      realName: info.value.realName || ''
    }
  }
})
</script>

<style scoped>
.page {
  height: 100%;
}
.card {
  background: #ffffff;
  border: 1px solid #ebeef5;
  border-radius: 12px;
  padding: 18px 20px;
}
.title {
  font-size: 16px;
  font-weight: 700;
  color: #111827;
}
.desc {
  margin-top: 8px;
  font-size: 12px;
  color: #6b7280;
}
.content {
  margin-top: 14px;
}
.wrap {
  max-width: 860px;
  margin: 0 auto;
}
.wrap.wrap-wide {
  max-width: none;
  margin: 0;
}
.avatar-uploader {
  display: inline-flex;
}
.avatar-upload-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
}
.avatar-click-area {
  position: relative;
  border-radius: 999px;
  overflow: hidden;
  cursor: pointer;
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.avatar-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  color: #ffffff;
  background: rgba(17, 24, 39, 0.45);
  opacity: 0;
  transition: opacity 0.15s ease;
  pointer-events: none;
}
.avatar-uploader:hover .avatar-click-area {
  transform: scale(1.03);
  box-shadow: 0 10px 24px rgba(17, 24, 39, 0.18);
}
.avatar-uploader:hover .avatar-overlay {
  opacity: 1;
}
.avatar-tip {
  margin-top: 6px;
  font-size: 12px;
  color: #6b7280;
  line-height: 1;
}
.top {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 14px;
  justify-content: center;
}
.top-right {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
  align-items: center;
}
.name {
  font-size: 16px;
  font-weight: 700;
  color: #111827;
  max-width: 340px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.sub {
  font-size: 12px;
  color: #6b7280;
}
.grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px 24px;
  max-width: 760px;
  margin: 0 auto;
}
.row {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 8px;
  min-height: 42px;
}
.label {
  width: auto;
  text-align: left;
  font-size: 13px;
  color: #6b7280;
  flex: 0 0 auto;
}
.value {
  min-width: 0;
  max-width: 360px;
  padding: 0;
  border: none;
  background: transparent;
  color: #111827;
  font-size: 13px;
  text-align: left;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1 1 auto;
}
.value-input {
  min-width: 0;
  max-width: 360px;
  flex: 1 1 auto;
}
.row.row-span {
  grid-column: 1 / -1;
}
.row.row-span .value-input {
  max-width: none;
  width: 100%;
}
.actions {
  display: flex;
  justify-content: center;
  margin-top: 18px;
}
.action-tile {
  width: min(520px, 100%);
  border-radius: 14px;
  padding: 14px 16px;
  border: 1px solid #e5e7eb;
  background: linear-gradient(180deg, #ffffff 0%, #fbfcff 100%);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  cursor: pointer;
  user-select: none;
  box-shadow: 0 0 0 rgba(0, 0, 0, 0);
  transition:
    transform 160ms ease,
    box-shadow 160ms ease,
    border-color 160ms ease,
    background 160ms ease;
}
.action-tile:hover {
  transform: translateY(-1px);
  box-shadow: 0 10px 24px rgba(17, 24, 39, 0.08);
  border-color: #c7d2fe;
  background: linear-gradient(180deg, #ffffff 0%, #f6f8ff 100%);
}
.action-tile:active {
  transform: translateY(0);
  box-shadow: 0 6px 14px rgba(17, 24, 39, 0.08);
}
.action-tile:focus-visible {
  outline: 0;
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.25);
  border-color: #6366f1;
}
.action-tile-left {
  min-width: 0;
}
.action-tile-title {
  font-size: 15px;
  font-weight: 800;
  color: #111827;
  letter-spacing: 0.2px;
}
.action-tile-sub {
  margin-top: 4px;
  font-size: 12px;
  color: #6b7280;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.action-tile-arrow {
  flex: none;
  width: 34px;
  height: 34px;
  border-radius: 999px;
  display: grid;
  place-items: center;
  background: rgba(99, 102, 241, 0.1);
  color: #4f46e5;
  font-size: 16px;
  font-weight: 800;
  transition: transform 160ms ease, background 160ms ease;
}
.action-tile:hover .action-tile-arrow {
  transform: translateX(2px);
  background: rgba(99, 102, 241, 0.14);
}
.action-tile.no-arrow {
  justify-content: flex-start;
}
.action-tile.disabled {
  opacity: 0.75;
  cursor: not-allowed;
}
.action-tile.disabled:hover {
  transform: none;
  box-shadow: 0 0 0 rgba(0, 0, 0, 0);
  border-color: #e5e7eb;
  background: linear-gradient(180deg, #ffffff 0%, #fbfcff 100%);
}
.action-tile.disabled:hover .action-tile-arrow {
  transform: none;
  background: rgba(99, 102, 241, 0.1);
}
.action-tile.danger {
  border-color: #fee2e2;
  background: linear-gradient(180deg, #ffffff 0%, #fff7f7 100%);
}
.action-tile.danger:hover {
  border-color: #fecaca;
  background: linear-gradient(180deg, #ffffff 0%, #fff1f1 100%);
}
.action-tile.danger:focus-visible {
  box-shadow: 0 0 0 3px rgba(220, 38, 38, 0.22);
  border-color: #ef4444;
}
.action-tile.danger .action-tile-arrow {
  background: rgba(220, 38, 38, 0.1);
  color: #dc2626;
}
.action-tile.danger:hover .action-tile-arrow {
  background: rgba(220, 38, 38, 0.14);
}
.action-tile.danger.disabled:hover .action-tile-arrow {
  background: rgba(220, 38, 38, 0.1);
}
.security {
  max-width: 760px;
  margin: 0 auto;
}
.security-section {
  padding: 2px 0;
}
.security-title {
  font-size: 14px;
  font-weight: 700;
  color: #111827;
  text-align: left;
  margin-bottom: 10px;
}
.security-title.danger {
  color: #b91c1c;
}
.security-desc {
  font-size: 12px;
  color: #6b7280;
  margin-bottom: 12px;
}
.security-actions {
  display: flex;
  justify-content: center;
  margin-top: 14px;
}
.security-divider {
  height: 1px;
  background: #ebeef5;
  margin: 16px auto;
  max-width: 760px;
}
.mentor {
  max-width: 760px;
  margin: 0 auto;
}
.mentor-actions {
  display: flex;
  justify-content: center;
  margin-top: 16px;
}
.academic {
  max-width: 760px;
  margin: 0 auto;
}
.teacher-info {
  max-width: 760px;
  margin: 0 auto;
}
.academic-school {
  margin-bottom: 14px;
  padding-bottom: 6px;
  position: relative;
}
.academic-school-k {
  font-size: 12px;
  color: #6b7280;
}
.academic-school-v {
  margin-top: 6px;
  font-size: 22px;
  font-weight: 900;
  color: #111827;
  line-height: 1.25;
  word-break: break-word;
  display: inline-block;
  position: relative;
}
.academic-school-v::after {
  content: '';
  position: absolute;
  left: -4px;
  right: -4px;
  bottom: -4px;
  height: 10px;
  border-radius: 999px;
  background: linear-gradient(90deg, rgba(99, 102, 241, 0.22), rgba(59, 130, 246, 0));
  z-index: -1;
}
.academic .grid {
  margin: 0;
}
.mentor-empty {
  margin-top: 8px;
  font-size: 12px;
  color: #6b7280;
  text-align: center;
}
.mentor-top {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 14px;
  justify-content: center;
}
.mentor-top-right {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
  align-items: center;
}
.mentor-name {
  font-size: 16px;
  font-weight: 700;
  color: #111827;
  max-width: 340px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.mentor-sub {
  font-size: 12px;
  color: #6b7280;
}
.materials {
  width: 100%;
}
.materials-bar {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}
.materials-bar-left {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  align-items: center;
}
.materials-bar-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}
.materials-bar-right {
  margin-left: auto;
}
.materials-table-wrap {
  border: 1px solid #ebeef5;
  border-radius: 10px;
  overflow: hidden;
}
.materials-title {
  max-width: 420px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.materials-pager {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  margin-top: 14px;
}
@media (max-width: 900px) {
  .grid {
    grid-template-columns: 1fr;
    gap: 12px;
    max-width: 520px;
  }
  .value {
    min-width: 0;
  }
  .value-input {
    min-width: 0;
  }
}
</style>
