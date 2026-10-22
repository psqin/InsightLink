package com.psqin.service.Impl;

import com.github.pagehelper.Page;
import com.github.pagehelper.PageHelper;
import com.psqin.constant.MessageConstant;
import com.psqin.domain.entity.SysDept;
import com.psqin.exception.AccountNotAllowException;
import com.psqin.mapper.SysDeptMapper;
import com.psqin.result.PageResult;
import com.psqin.service.SysDeptService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Service
public class SysDeptServiceImpl implements SysDeptService {

    @Autowired
    private SysDeptMapper sysDeptMapper;

    @Override
    public List<SysDept> listCollegesByUniversityId(Long universityId) {
        if (universityId == null) {
            throw new AccountNotAllowException(MessageConstant.DATA_NOT_FOUND);
        }
        return sysDeptMapper.listCollegesByUniversityId(universityId);
    }

    @Override
    public List<SysDept> listMajorsByCollegeId(Long collegeId) {
        if (collegeId == null) {
            throw new AccountNotAllowException(MessageConstant.DATA_NOT_FOUND);
        }
        return sysDeptMapper.listMajorsByCollegeId(collegeId);
    }

    @Override
    public List<SysDept> listClassesByMajorId(Long majorId) {
        if (majorId == null) {
            throw new AccountNotAllowException(MessageConstant.DATA_NOT_FOUND);
        }
        return sysDeptMapper.listClassesByMajorId(majorId);
    }

    @Override
    @Transactional
    public void save(SysDept sysDept) {
        validateForSaveOrUpdate(sysDept, false);
        sysDeptMapper.insert(sysDept);
    }

    @Override
    @Transactional
    public void update(SysDept sysDept) {
        validateForSaveOrUpdate(sysDept, true);
        sysDeptMapper.update(sysDept);
    }

    @Override
    @Transactional
    public void deleteById(Long id) {
        if (id == null) {
            throw new AccountNotAllowException(MessageConstant.DATA_NOT_FOUND);
        }
        Integer count = sysDeptMapper.countByParentId(id);
        if (count != null && count > 0) {
            throw new AccountNotAllowException(MessageConstant.CANNOTMODIFIED);
        }
        sysDeptMapper.deleteById(id);
    }

    @Override
    public PageResult pageQuery(Long universityId, Integer deptType, Long parentId, String name, Integer page, Integer pageSize) {
        PageHelper.startPage(page, pageSize);
        Page<SysDept> p = sysDeptMapper.pageQuery(universityId, deptType, parentId, name);
        return new PageResult(p.getTotal(), p.getResult());
    }

    private void validateForSaveOrUpdate(SysDept sysDept, boolean requireId) {
        if (sysDept == null) {
            throw new AccountNotAllowException(MessageConstant.DATA_NOT_FOUND);
        }
        if (requireId && sysDept.getId() == null) {
            throw new AccountNotAllowException(MessageConstant.DATA_NOT_FOUND);
        }
        if (sysDept.getName() == null || sysDept.getName().isEmpty()) {
            throw new AccountNotAllowException(MessageConstant.DATA_NOT_FOUND);
        }
        if (sysDept.getDeptType() == null || sysDept.getUniversityId() == null) {
            throw new AccountNotAllowException(MessageConstant.DATA_NOT_FOUND);
        }

        Integer deptType = sysDept.getDeptType();
        Long parentId = sysDept.getParentId();

        if (deptType == 1) {
            if (parentId != null) {
                throw new AccountNotAllowException(MessageConstant.HIERARCHY_ERROR);
            }
            return;
        }

        if (deptType == 2) {
            if (parentId == null) {
                throw new AccountNotAllowException(MessageConstant.HIERARCHY_ERROR);
            }
            Integer count = sysDeptMapper.countValidHierarchy(sysDept.getUniversityId(), parentId, null, null);
            if (count == null || count == 0) {
                throw new AccountNotAllowException(MessageConstant.HIERARCHY_ERROR);
            }
            return;
        }

        if (deptType == 3) {
            if (parentId == null) {
                throw new AccountNotAllowException(MessageConstant.HIERARCHY_ERROR);
            }
            SysDept major = sysDeptMapper.getById(parentId);
            if (major == null || major.getDeptType() == null || major.getDeptType() != 2 || major.getUniversityId() == null) {
                throw new AccountNotAllowException(MessageConstant.HIERARCHY_ERROR);
            }
            Long collegeId = major.getParentId();
            if (collegeId == null) {
                throw new AccountNotAllowException(MessageConstant.HIERARCHY_ERROR);
            }
            Integer count = sysDeptMapper.countValidHierarchy(sysDept.getUniversityId(), collegeId, major.getId(), null);
            if (count == null || count == 0) {
                throw new AccountNotAllowException(MessageConstant.HIERARCHY_ERROR);
            }
            return;
        }

        throw new AccountNotAllowException(MessageConstant.HIERARCHY_ERROR);
    }
}

