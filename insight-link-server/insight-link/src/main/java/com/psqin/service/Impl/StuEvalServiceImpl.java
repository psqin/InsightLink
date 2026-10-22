package com.psqin.service.Impl;

import com.github.pagehelper.Page;
import com.github.pagehelper.PageHelper;
import com.psqin.constant.MessageConstant;
import com.psqin.context.BaseContext;
import com.psqin.domain.dto.StuEvalDTO;
import com.psqin.domain.dto.StuMatTeaSearchPageDTO;
import com.psqin.domain.entity.StudentEvaluation;
import com.psqin.domain.entity.Teachers;
import com.psqin.domain.vo.StuMaterialPageVO;
import com.psqin.exception.AccountNotAllowException;
import com.psqin.exception.BaseException;
import com.psqin.mapper.StuEvalMapper;
import com.psqin.mapper.StuMaterialMapper;
import com.psqin.mapper.TeacherMapper;
import com.psqin.result.PageResult;
import com.psqin.service.StuEvalService;
import org.springframework.beans.BeanUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;

@Service
public class StuEvalServiceImpl implements StuEvalService {

    @Autowired
    private StuEvalMapper stuEvalMapper;

    @Autowired
    private StuMaterialMapper stuMaterialMapper;

    @Autowired
    private TeacherMapper teacherMapper;

    @Override
    public void save(StuEvalDTO stuEvalDTO) {
        Long materialId = stuEvalDTO.getMaterialId();
        // 检查是否已经评价过
        Integer count = stuEvalMapper.countByMaterialId(materialId);
        if (count > 0) {
            throw new AccountNotAllowException("该材料已评价，无法再次评价");
        }

        StudentEvaluation studentEvaluation = new StudentEvaluation();
        BeanUtils.copyProperties(stuEvalDTO, studentEvaluation);
        Long userId = BaseContext.getCurrentId();
        studentEvaluation.setTeacherUserId(userId);
        studentEvaluation.setEvaluationTime(LocalDateTime.now());
        try {
            stuEvalMapper.insert(studentEvaluation);
        } catch (Exception e) {
            throw new BaseException("评价内容不能为空");
        }

    }

    @Override
    public void delete(Long id) {
        // 校验是否存在且是否是当前导师的评价
        StudentEvaluation evaluation = stuEvalMapper.getById(id);
        if (evaluation == null) {
            throw new AccountNotAllowException("评价不存在");
        }
        Long userId = BaseContext.getCurrentId();
        if (!evaluation.getTeacherUserId().equals(userId)) {
            throw new AccountNotAllowException("无权删除他人评价");
        }
        stuEvalMapper.deleteById(id);
    }

    @Override
    public void deleteByAdmin(Long id) {
        Integer roleId = BaseContext.getRoleId();
        if (roleId == null || roleId != 1) {
            throw new AccountNotAllowException(MessageConstant.ACCOUNT_INSUFFICIENT_PERMISSIONS);
        }
        StudentEvaluation evaluation = stuEvalMapper.getById(id);
        if (evaluation == null) {
            throw new AccountNotAllowException("评价不存在");
        }
        stuEvalMapper.deleteById(id);
    }

    @Override
    public void update(StuEvalDTO stuEvalDTO) {
        Long id = stuEvalDTO.getId();
        StudentEvaluation evaluation = stuEvalMapper.getById(id);
        if (evaluation == null) {
            throw new AccountNotAllowException("评价不存在");
        }
        Long userId = BaseContext.getCurrentId();
        if (!evaluation.getTeacherUserId().equals(userId)) {
            throw new AccountNotAllowException("无权修改他人评价");
        }

        evaluation.setScore(stuEvalDTO.getScore());
        evaluation.setContent(stuEvalDTO.getContent());
        evaluation.setEvaluationTime(LocalDateTime.now());
        stuEvalMapper.update(evaluation);
    }

    @Override
    public StudentEvaluation getById(Long id) {
        StudentEvaluation evaluation = stuEvalMapper.getById(id);
        if (evaluation == null) {
            throw new AccountNotAllowException("评价不存在");
        }
        Long userId = BaseContext.getCurrentId();
        if (!evaluation.getTeacherUserId().equals(userId)) {
            throw new AccountNotAllowException("无权查看他人评价");
        }
        return evaluation;
    }

    @Override
    public PageResult pageQueryMaterials(StuMatTeaSearchPageDTO dto) {
        Long teacherId = BaseContext.getCurrentId();
        Teachers teacher = teacherMapper.getById(teacherId);
        if (teacher != null) {
            dto.setUniversityId(teacher.getUniversityId());
            dto.setCollegeId(teacher.getDeptId());
        }
        PageHelper.startPage(dto.getPage(), dto.getPageSize());
        Page<StuMaterialPageVO> page = stuMaterialMapper.pageQueryForTeacher(dto, teacherId);
        return new PageResult(page.getTotal(), page.getResult());
    }

    @Override
    public PageResult pageQueryMaterialsByAdmin(StuMatTeaSearchPageDTO dto) {
        Integer roleId = BaseContext.getRoleId();
        if (roleId == null || roleId != 1) {
            throw new AccountNotAllowException(MessageConstant.ACCOUNT_INSUFFICIENT_PERMISSIONS);
        }
        PageHelper.startPage(dto.getPage(), dto.getPageSize());
        Page<StuMaterialPageVO> page = stuMaterialMapper.pageQueryForAdmin(dto);
        return new PageResult(page.getTotal(), page.getResult());
    }
}
