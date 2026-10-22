package com.psqin.service.Impl;

import com.github.pagehelper.Page;
import com.github.pagehelper.PageHelper;
import com.psqin.constant.MessageConstant;
import com.psqin.constant.StatusConstant;
import com.psqin.context.BaseContext;
import com.psqin.domain.dto.AdminStudentSearchDTO;
import com.psqin.domain.dto.StudentInfoDTO;
import com.psqin.domain.dto.StudentSearchDTO;
import com.psqin.domain.dto.UserDTO;
import com.psqin.domain.entity.Students;
import com.psqin.domain.entity.Universities;
import com.psqin.domain.entity.User;
import com.psqin.domain.vo.StudentVO;
import com.psqin.domain.vo.StudentsPageVO;
import com.psqin.domain.vo.TeacherVO;
import com.psqin.exception.AccountNotAllowException;
import com.psqin.mapper.StudentMapper;
import com.psqin.mapper.SysDeptMapper;
import com.psqin.mapper.TeacherMapper;
import com.psqin.mapper.TsGuidanceMapper;
import com.psqin.result.PageResult;
import com.psqin.service.StudentService;
import com.psqin.service.UniversityService;
import com.psqin.service.UserService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.BeanUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.DigestUtils;

/**
 *
 */
@Slf4j
@Service
public class StudentServiceImpl implements StudentService {

    @Autowired
    private StudentMapper studentMapper;

    @Autowired
    private TsGuidanceMapper tsGuidanceMapper;

    @Autowired
    private UniversityService universityService;

    @Autowired
    private SysDeptMapper sysDeptMapper;

    @Autowired
    private TeacherMapper teacherMapper;

    @Override
    @Transactional
    public void save(StudentInfoDTO studentInfoDTO) {
        Long id = BaseContext.getCurrentId();
        Students students = studentMapper.getByUserId(id);
        if (students != null) {
            throw new AccountNotAllowException(MessageConstant.ALREADY_EXISTS);
        }

        // 校验学校、学院、专业、班级的层级关系是否正确
        Integer count = sysDeptMapper.countValidHierarchy(
                studentInfoDTO.getUniversityId(),
                studentInfoDTO.getCollegeId(),
                studentInfoDTO.getMajorId(),
                studentInfoDTO.getClassId());
        if (count == null || count == 0) {
            throw new AccountNotAllowException(MessageConstant.HIERARCHY_ERROR);
        }

        Students student = new Students();
        BeanUtils.copyProperties(studentInfoDTO, student);
        student.setUserId(id);

        studentMapper.insert(student);
    }

    @Override
    public PageResult pageQuery(StudentSearchDTO studentSearchDTO, Long universityId, Long deptId) {
        PageHelper.startPage(studentSearchDTO.getPage(),studentSearchDTO.getPageSize());
        Students student = new Students();
        BeanUtils.copyProperties(studentSearchDTO,student);
        student.setUniversityId(universityId);
        student.setCollegeId(deptId);
        student.setBindStatus(StatusConstant.STUDENT_UNBOUND);
        Page<StudentsPageVO> page = studentMapper.pageQuery(student);
        return new PageResult(page.getTotal(),page.getResult());
    }

    @Override
    public StudentVO getStudentInfo() {
        Long userId = BaseContext.getCurrentId();
        StudentVO studentVO = studentMapper.getStudentInfoByUserId(userId);
        return studentVO;
    }

    @Override
    public TeacherVO getMyTeacherInfo() {
        Long studentUserId = BaseContext.getCurrentId();
        Long teacherUserId = tsGuidanceMapper.getTeacherUserIdByStudentUserId(studentUserId);
        if (teacherUserId == null) {
            throw new AccountNotAllowException("未绑定导师");
        }
        TeacherVO teacherVO = teacherMapper.getTeacherInfoByUserId(teacherUserId);
        if (teacherVO == null) {
            throw new AccountNotAllowException("导师信息不存在");
        }
        return teacherVO;
    }

    @Override
    @Transactional
    public void update(StudentInfoDTO studentInfoDTO) {
        Long userId = BaseContext.getCurrentId();
        Students students = studentMapper.getByUserId(userId);
        if (students == null) {
            throw new AccountNotAllowException("学生信息不存在");
        }

        // 校验学校、学院、专业、班级的层级关系是否正确
        Integer count = sysDeptMapper.countValidHierarchy(
                studentInfoDTO.getUniversityId(),
                studentInfoDTO.getCollegeId(),
                studentInfoDTO.getMajorId(),
                studentInfoDTO.getClassId());
        if (count == null || count == 0) {
            throw new AccountNotAllowException(MessageConstant.HIERARCHY_ERROR);
        }

        // 检查是否修改了学校或学院
        boolean isUniversityOrCollegeChanged = !students.getUniversityId().equals(studentInfoDTO.getUniversityId())
                || !students.getCollegeId().equals(studentInfoDTO.getCollegeId());

        Students updateStudent = new Students();
        BeanUtils.copyProperties(studentInfoDTO, updateStudent);
        updateStudent.setId(students.getId());

        if (isUniversityOrCollegeChanged) {
            // 如果修改了学校或学院，删除绑定状态和绑定关系
            updateStudent.setBindStatus(StatusConstant.STUDENT_UNBOUND);
            tsGuidanceMapper.deleteByStudentUserId(userId);
        } else {
            // 否则保留原有绑定状态
            updateStudent.setBindStatus(students.getBindStatus());
        }

        studentMapper.update(updateStudent);
    }

    @Override
    public PageResult adminPageQuery(AdminStudentSearchDTO adminStudentSearchDTO) {
        Integer roleId = BaseContext.getRoleId();
        if (roleId == null || roleId != 1) {
            throw new AccountNotAllowException(MessageConstant.ACCOUNT_INSUFFICIENT_PERMISSIONS);
        }
        PageHelper.startPage(adminStudentSearchDTO.getPage(), adminStudentSearchDTO.getPageSize());
        Page<StudentVO> p = studentMapper.pageQueryAdmin(adminStudentSearchDTO);
        return new PageResult(p.getTotal(), p.getResult());
    }

    @Override
    @Transactional
    public void adminUpdate(Long studentId, StudentInfoDTO studentInfoDTO) {
        Integer roleId = BaseContext.getRoleId();
        if (roleId == null || roleId != 1) {
            throw new AccountNotAllowException(MessageConstant.ACCOUNT_INSUFFICIENT_PERMISSIONS);
        }
        Students students = studentMapper.getById(studentId);
        if (students == null) {
            throw new AccountNotAllowException("学生信息不存在");
        }

        Integer count = sysDeptMapper.countValidHierarchy(
                studentInfoDTO.getUniversityId(),
                studentInfoDTO.getCollegeId(),
                studentInfoDTO.getMajorId(),
                studentInfoDTO.getClassId());
        if (count == null || count == 0) {
            throw new AccountNotAllowException(MessageConstant.HIERARCHY_ERROR);
        }

        boolean isUniversityOrCollegeChanged = !students.getUniversityId().equals(studentInfoDTO.getUniversityId())
                || !students.getCollegeId().equals(studentInfoDTO.getCollegeId());

        Students updateStudent = new Students();
        BeanUtils.copyProperties(studentInfoDTO, updateStudent);
        updateStudent.setId(students.getId());

        if (isUniversityOrCollegeChanged) {
            updateStudent.setBindStatus(StatusConstant.STUDENT_UNBOUND);
            tsGuidanceMapper.deleteByStudentUserId(students.getUserId());
        } else {
            updateStudent.setBindStatus(students.getBindStatus());
        }

        studentMapper.update(updateStudent);
    }

    @Override
    @Transactional
    public void adminDelete(Long studentId) {
        Integer roleId = BaseContext.getRoleId();
        if (roleId == null || roleId != 1) {
            throw new AccountNotAllowException(MessageConstant.ACCOUNT_INSUFFICIENT_PERMISSIONS);
        }
        Students students = studentMapper.getById(studentId);
        if (students == null) {
            throw new AccountNotAllowException("学生信息不存在");
        }
        tsGuidanceMapper.deleteByStudentUserId(students.getUserId());
        studentMapper.deleteById(studentId);
    }

    @Override
    public StudentVO adminGetDetail(Long studentId) {
        Integer roleId = BaseContext.getRoleId();
        if (roleId == null || roleId != 1) {
            throw new AccountNotAllowException(MessageConstant.ACCOUNT_INSUFFICIENT_PERMISSIONS);
        }
        StudentVO vo = studentMapper.getStudentInfoByStudentId(studentId);
        if (vo == null) {
            throw new AccountNotAllowException("学生信息不存在");
        }
        return vo;
    }
}
