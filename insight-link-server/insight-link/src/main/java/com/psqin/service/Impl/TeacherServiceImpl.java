package com.psqin.service.Impl;

import com.psqin.constant.MessageConstant;
import com.psqin.context.BaseContext;
import com.psqin.domain.dto.AdminTeacherSearchDTO;
import com.psqin.domain.dto.StudentSearchDTO;
import com.psqin.domain.dto.TeacherInfoDTO;
import com.psqin.domain.entity.Teachers;
import com.psqin.domain.entity.Universities;
import com.psqin.domain.entity.User;
import com.psqin.domain.vo.TeacherVO;
import com.github.pagehelper.Page;
import com.github.pagehelper.PageHelper;
import com.psqin.exception.AccountNotAllowException;
import com.psqin.exception.BaseException;
import com.psqin.mapper.StudentMapper;
import com.psqin.mapper.SysDeptMapper;
import com.psqin.mapper.TeacherMapper;
import com.psqin.mapper.TsGuidanceMapper;
import com.psqin.mapper.UserMapper;
import com.psqin.result.PageResult;
import com.psqin.service.StudentService;
import com.psqin.service.TeacherService;
import com.psqin.service.UniversityService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.BeanUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 *
 */
@Slf4j
@Service
public class TeacherServiceImpl implements TeacherService {

    @Autowired
    private TeacherMapper teacherMapper;

    @Autowired
    private UserMapper userMapper;

    @Autowired
    private UniversityService universityService;

    @Autowired
    private StudentService studentService;

    @Autowired
    private SysDeptMapper sysDeptMapper;

    @Autowired
    private TsGuidanceMapper tsGuidanceMapper;

    @Autowired
    private StudentMapper studentMapper;


    @Override
    @Transactional
    public void save(TeacherInfoDTO teacherInfoDTO) {
        Long id = BaseContext.getCurrentId();
        Teachers teachers = teacherMapper.getByUserId(id);
        if (teachers != null) {
            throw new AccountNotAllowException(MessageConstant.ALREADY_EXISTS);
        }

        // 校验学校和院系的关联关系是否正确
        Integer count = sysDeptMapper.countValidHierarchy(
                teacherInfoDTO.getUniversityId(),
                teacherInfoDTO.getDeptId(),
                null,
                null);
        if (count == null || count == 0) {
            throw new AccountNotAllowException(MessageConstant.HIERARCHY_ERROR);
        }

        Teachers teacher = new Teachers();
        BeanUtils.copyProperties(teacherInfoDTO, teacher);
        teacher.setUserId(id);

        teacherMapper.insert(teacher);
    }

    @Override
    public PageResult pageQuery(StudentSearchDTO studentSearchDTO) {
        Long userId = BaseContext.getCurrentId();
        Teachers teacher = getById(userId);
        if (teacher == null) {
            throw new BaseException("请完善导师信息");
        }
        Long universityId = teacher.getUniversityId();
        Long deptId = teacher.getDeptId();
        PageResult pageResult = studentService.pageQuery(studentSearchDTO,universityId,deptId);
        return pageResult;
    }

    @Override
    public Teachers getById(Long userId) {
        return teacherMapper.getById(userId);
    }

    @Override
    public TeacherVO getTeacherInfo() {
        Long userId = BaseContext.getCurrentId();
        return teacherMapper.getTeacherInfoByUserId(userId);
    }

    @Override
    @Transactional
    public void update(TeacherInfoDTO teacherInfoDTO) {
        Long userId = BaseContext.getCurrentId();
        Teachers teachers = teacherMapper.getByUserId(userId);
        if (teachers == null) {
            throw new AccountNotAllowException("导师信息不存在");
        }

        // 校验学校和院系的关联关系是否正确
        Integer count = sysDeptMapper.countValidHierarchy(
                teacherInfoDTO.getUniversityId(),
                teacherInfoDTO.getDeptId(),
                null,
                null);
        if (count == null || count == 0) {
            throw new AccountNotAllowException(MessageConstant.HIERARCHY_ERROR);
        }

        // 检查是否修改了学校或学院
        boolean isUniversityOrDeptChanged = !teachers.getUniversityId().equals(teacherInfoDTO.getUniversityId())
                || !teachers.getDeptId().equals(teacherInfoDTO.getDeptId());

        Teachers updateTeacher = new Teachers();
        BeanUtils.copyProperties(teacherInfoDTO, updateTeacher);
        updateTeacher.setId(teachers.getId());

        if (isUniversityOrDeptChanged) {
            // 如果修改了学校或学院，删除绑定表所有的绑定关系，同时修改学生的绑定状态
            // 1. 先把该导师绑定的所有学生的绑定状态设置为未绑定
            studentMapper.unbindByTeacherId(teachers.getId());
            // 2. 删除该导师在绑定表中的所有记录
            tsGuidanceMapper.deleteByTeacherUserId(userId);
        }

        teacherMapper.update(updateTeacher);
    }

    @Override
    public PageResult adminPageQuery(AdminTeacherSearchDTO adminTeacherSearchDTO) {
        Integer roleId = BaseContext.getRoleId();
        if (roleId == null || roleId != 1) {
            throw new AccountNotAllowException(MessageConstant.ACCOUNT_INSUFFICIENT_PERMISSIONS);
        }
        PageHelper.startPage(adminTeacherSearchDTO.getPage(), adminTeacherSearchDTO.getPageSize());
        Page<TeacherVO> p = teacherMapper.pageQueryAdmin(adminTeacherSearchDTO);
        return new PageResult(p.getTotal(), p.getResult());
    }

    @Override
    @Transactional
    public void adminUpdate(Long teacherId, TeacherInfoDTO teacherInfoDTO) {
        Integer roleId = BaseContext.getRoleId();
        if (roleId == null || roleId != 1) {
            throw new AccountNotAllowException(MessageConstant.ACCOUNT_INSUFFICIENT_PERMISSIONS);
        }
        Teachers teachers = teacherMapper.getEntityById(teacherId);
        if (teachers == null) {
            throw new AccountNotAllowException("导师信息不存在");
        }

        Integer count = sysDeptMapper.countValidHierarchy(
                teacherInfoDTO.getUniversityId(),
                teacherInfoDTO.getDeptId(),
                null,
                null);
        if (count == null || count == 0) {
            throw new AccountNotAllowException(MessageConstant.HIERARCHY_ERROR);
        }

        boolean isUniversityOrDeptChanged = !teachers.getUniversityId().equals(teacherInfoDTO.getUniversityId())
                || !teachers.getDeptId().equals(teacherInfoDTO.getDeptId());

        Teachers updateTeacher = new Teachers();
        BeanUtils.copyProperties(teacherInfoDTO, updateTeacher);
        updateTeacher.setId(teachers.getId());

        if (isUniversityOrDeptChanged) {
            studentMapper.unbindByTeacherUserId(teachers.getUserId());
            tsGuidanceMapper.deleteByTeacherUserId(teachers.getUserId());
        }

        teacherMapper.update(updateTeacher);
    }

    @Override
    @Transactional
    public void adminDelete(Long teacherId) {
        Integer roleId = BaseContext.getRoleId();
        if (roleId == null || roleId != 1) {
            throw new AccountNotAllowException(MessageConstant.ACCOUNT_INSUFFICIENT_PERMISSIONS);
        }
        Teachers teachers = teacherMapper.getEntityById(teacherId);
        if (teachers == null) {
            throw new AccountNotAllowException("导师信息不存在");
        }
        studentMapper.unbindByTeacherUserId(teachers.getUserId());
        tsGuidanceMapper.deleteByTeacherUserId(teachers.getUserId());
        teacherMapper.deleteById(teacherId);
    }

    @Override
    public TeacherVO adminGetDetail(Long teacherId) {
        Integer roleId = BaseContext.getRoleId();
        if (roleId == null || roleId != 1) {
            throw new AccountNotAllowException(MessageConstant.ACCOUNT_INSUFFICIENT_PERMISSIONS);
        }
        Teachers teachers = teacherMapper.getEntityById(teacherId);
        if (teachers == null) {
            throw new AccountNotAllowException("导师信息不存在");
        }
        TeacherVO vo = teacherMapper.getTeacherInfoByUserId(teachers.getUserId());
        if (vo == null) {
            throw new AccountNotAllowException("导师信息不存在");
        }
        return vo;
    }
}
