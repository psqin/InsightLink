package com.psqin.service.Impl;

import com.github.pagehelper.Page;
import com.github.pagehelper.PageHelper;
import com.psqin.constant.MessageConstant;
import com.psqin.context.BaseContext;
import com.psqin.domain.dto.StudentMaterialDTO;
import com.psqin.domain.dto.StudentMaterialPageDTO;
import com.psqin.domain.entity.StudentMaterial;
import com.psqin.domain.vo.StudentMaterialVO;
import com.psqin.exception.AccountNotAllowException;
import com.psqin.mapper.StuEvalMapper;
import com.psqin.mapper.StuMaterialMapper;
import com.psqin.mapper.TsGuidanceMapper;
import com.psqin.result.PageResult;
import com.psqin.service.StuMaterialService;
import org.springframework.beans.BeanUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

@Service
public class StuMaterialServiceImpl implements StuMaterialService {

    @Autowired
    private StuMaterialMapper stuMaterialMapper;

    @Autowired
    private StuEvalMapper stuEvalMapper;

    @Autowired
    private TsGuidanceMapper tsGuidanceMapper;

    @Override
    public void save(StudentMaterialDTO studentMaterialDTO) {
        Long userId = BaseContext.getCurrentId();
        StudentMaterial studentMaterial = new StudentMaterial();
        BeanUtils.copyProperties(studentMaterialDTO,studentMaterial);
        studentMaterial.setStudentUserId(userId);
        stuMaterialMapper.insert(studentMaterial);
    }

    @Override
    public void delete(Long id) {
        // 校验是否是当前用户的材料
        StudentMaterial material = stuMaterialMapper.getById(id);
        if (material == null) {
            throw new AccountNotAllowException("材料不存在");
        }
        Long currentId = BaseContext.getCurrentId();
        if (!material.getStudentUserId().equals(currentId)) {
            throw new AccountNotAllowException("无权操作");
        }
        // 检查是否有评价
        Integer count = stuEvalMapper.countByMaterialId(id);
        if (count > 0) {
            throw new AccountNotAllowException("材料已评价，无法删除");
        }
        stuMaterialMapper.deleteById(id);
    }

    @Override
    public void deleteByAdmin(Long id) {
        Integer roleId = BaseContext.getRoleId();
        if (roleId == null || roleId != 1) {
            throw new AccountNotAllowException(MessageConstant.ACCOUNT_INSUFFICIENT_PERMISSIONS);
        }
        StudentMaterial material = stuMaterialMapper.getById(id);
        if (material == null) {
            throw new AccountNotAllowException("材料不存在");
        }
        stuEvalMapper.deleteByMaterialId(id);
        stuMaterialMapper.deleteById(id);
    }

    @Override
    public void update(StudentMaterialDTO studentMaterialDTO) {
        Long id = studentMaterialDTO.getId();
        StudentMaterial material = stuMaterialMapper.getById(id);
        if (material == null) {
            throw new AccountNotAllowException("材料不存在");
        }
        Long currentId = BaseContext.getCurrentId();
        if (!material.getStudentUserId().equals(currentId)) {
            throw new AccountNotAllowException("无权操作");
        }
        // 检查是否有评价
        Integer count = stuEvalMapper.countByMaterialId(id);
        if (count > 0) {
            throw new AccountNotAllowException("材料已评价，无法修改");
        }

        StudentMaterial updateMaterial = new StudentMaterial();
        BeanUtils.copyProperties(studentMaterialDTO, updateMaterial);
        stuMaterialMapper.update(updateMaterial);
    }

    @Override
    public StudentMaterialVO getById(Long id) {
        StudentMaterialVO materialVO = stuMaterialMapper.getByIdWithEvaluation(id);
        if (materialVO == null) {
            throw new AccountNotAllowException("材料不存在");
        }
        Integer roleId = BaseContext.getRoleId();
        if (roleId != null && roleId == 1) {
            return materialVO;
        }
        // 允许导师或学生自己查看
        Long currentId = BaseContext.getCurrentId();
        // 1. 如果是学生自己
        if (materialVO.getStudentUserId().equals(currentId)) {
            return materialVO;
        }
        // 2. 如果是绑定导师
        Integer count = tsGuidanceMapper.countByTeacherAndStudent(currentId, materialVO.getStudentUserId());
        if (count != null && count > 0) {
            return materialVO;
        }

        // 否则无权查看
        throw new AccountNotAllowException("无权查看");
    }

    @Override
    public PageResult pageQuery(StudentMaterialPageDTO studentMaterialPageDTO) {
        PageHelper.startPage(studentMaterialPageDTO.getPage(), studentMaterialPageDTO.getPageSize());
        Long userId = BaseContext.getCurrentId();

        StudentMaterial studentMaterial = new StudentMaterial();
        studentMaterial.setStudentUserId(userId);
        studentMaterial.setMaterialType(studentMaterialPageDTO.getMaterialType());
        studentMaterial.setTitle(studentMaterialPageDTO.getTitle());

        Page<StudentMaterialVO> page = stuMaterialMapper.pageQuery(studentMaterial);
        return new PageResult(page.getTotal(), page.getResult());
    }
}
