package com.psqin.service.Impl;

import com.github.pagehelper.Page;
import com.github.pagehelper.PageHelper;
import com.psqin.constant.StatusConstant;
import com.psqin.context.BaseContext;
import com.psqin.domain.dto.StudentSearchDTO;
import com.psqin.domain.entity.Students;
import com.psqin.domain.vo.StudentVO;
import com.psqin.domain.vo.StudentsPageVO;
import com.psqin.exception.AccountNotAllowException;
import com.psqin.exception.UpdateNotAllowedException;
import com.psqin.mapper.StudentMapper;
import com.psqin.mapper.TsGuidanceMapper;
import com.psqin.result.PageResult;
import com.psqin.service.TsGuidanceService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.Set;
import java.util.stream.Collectors;

@Service
public class TsGuidanceServiceImpl implements TsGuidanceService {

    @Autowired
    private TsGuidanceMapper tsGuidanceMapper;

    @Autowired
    private StudentMapper studentMapper;

    @Override
    @Transactional
    public void saveBatch(List<Long> ids) {
        if (ids == null || ids.isEmpty()) {
            return;
        }
        List<Long> distinctIds = ids.stream().distinct().collect(Collectors.toList());
        Long teacherUserId = BaseContext.getCurrentId();
        List<Students> students = studentMapper.listByUserIds(distinctIds);
        Set<Long> existingUserIds = students.stream().map(Students::getUserId).collect(Collectors.toSet());
        List<Long> missingUserIds = distinctIds.stream().filter(id -> !existingUserIds.contains(id)).collect(Collectors.toList());
        if (!missingUserIds.isEmpty()) {
            throw new UpdateNotAllowedException("学生不存在：" + missingUserIds);
        }

        List<Long> alreadyBoundUserIds = students.stream()
                .filter(s -> s.getBindStatus() != null && StatusConstant.STUDENT_BINDED.equals(s.getBindStatus()))
                .map(Students::getUserId)
                .collect(Collectors.toList());
        if (!alreadyBoundUserIds.isEmpty()) {
            throw new UpdateNotAllowedException("学生已绑定导师：" + alreadyBoundUserIds);
        }

        List<Long> alreadyLinkedToCurrentTeacher = tsGuidanceMapper.listStudentUserIdsByTeacherAndStudentIds(teacherUserId, distinctIds);
        if (alreadyLinkedToCurrentTeacher != null && !alreadyLinkedToCurrentTeacher.isEmpty()) {
            throw new UpdateNotAllowedException("学生已在当前导师名下绑定：" + alreadyLinkedToCurrentTeacher);
        }

        tsGuidanceMapper.saveByIds(distinctIds, teacherUserId);
        studentMapper.updateBindStatusByUserIds(distinctIds, StatusConstant.STUDENT_BINDED);
    }

    @Override
    @Transactional
    public void deleteBatch(List<Long> ids) {
        if (ids == null || ids.isEmpty()) {
            return;
        }
        List<Long> distinctIds = ids.stream().distinct().collect(Collectors.toList());
        Long teacherUserId = BaseContext.getCurrentId();
        List<Long> boundToCurrentTeacher = tsGuidanceMapper.listStudentUserIdsByTeacherAndStudentIds(teacherUserId, distinctIds);
        if (boundToCurrentTeacher == null || boundToCurrentTeacher.isEmpty()) {
            return;
        }
        tsGuidanceMapper.deleteByIds(boundToCurrentTeacher, teacherUserId);
        studentMapper.updateBindStatusByUserIds(boundToCurrentTeacher, StatusConstant.STUDENT_UNBOUND);
    }

    @Override
    public PageResult pageQuery(StudentSearchDTO studentSearchDTO) {
        PageHelper.startPage(studentSearchDTO.getPage(), studentSearchDTO.getPageSize());
        Long teacherUserId = BaseContext.getCurrentId();
        Page<StudentsPageVO> page = tsGuidanceMapper.pageQuery(studentSearchDTO, teacherUserId);
        return new PageResult(page.getTotal(), page.getResult());
    }

    @Override
    public StudentVO getStudentDetail(Long studentUserId) {
        Long teacherUserId = BaseContext.getCurrentId();
        // 校验该学生是否由当前导师指导
        Integer count = tsGuidanceMapper.countByTeacherAndStudent(teacherUserId, studentUserId);
        if (count == null || count == 0) {
            throw new AccountNotAllowException("无权查看该学生信息或未绑定");
        }
        return studentMapper.getStudentInfoByUserId(studentUserId);
    }
}
