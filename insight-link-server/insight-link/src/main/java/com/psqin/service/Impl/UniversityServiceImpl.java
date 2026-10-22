package com.psqin.service.Impl;

import com.github.pagehelper.Page;
import com.github.pagehelper.PageHelper;
import com.psqin.constant.MessageConstant;
import com.psqin.domain.entity.Universities;
import com.psqin.exception.AccountNotAllowException;
import com.psqin.mapper.UniversityMapper;
import com.psqin.result.PageResult;
import com.psqin.service.UniversityService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

/**
 *
 */
@Service
public class UniversityServiceImpl implements UniversityService {

    @Autowired
    private UniversityMapper universityMapper;


    /**
     * 模糊查询学校
     * @param name
     * @return
     */
    @Override
    public List<Universities> query(String name) {
        return universityMapper.query(name);
    }

    /**
     * 根据id获取学校信息
     * @param id
     * @return
     */
    @Override
    public Universities getById(long id) {
        return universityMapper.getById(id);
    }

    @Override
    @Transactional
    public void save(Universities universities) {
        if (universities == null || universities.getName() == null || universities.getName().isEmpty()) {
            throw new AccountNotAllowException(MessageConstant.DATA_NOT_FOUND);
        }
        universityMapper.insert(universities);
    }

    @Override
    @Transactional
    public void update(Universities universities) {
        if (universities == null || universities.getId() == null) {
            throw new AccountNotAllowException(MessageConstant.DATA_NOT_FOUND);
        }
        universityMapper.update(universities);
    }

    @Override
    @Transactional
    public void deleteById(Long id) {
        if (id == null) {
            throw new AccountNotAllowException(MessageConstant.DATA_NOT_FOUND);
        }
        universityMapper.deleteById(id);
    }

    @Override
    public PageResult pageQuery(String name, String code, Integer page, Integer pageSize) {
        PageHelper.startPage(page, pageSize);
        Page<Universities> p = universityMapper.pageQuery(name, code);
        return new PageResult(p.getTotal(), p.getResult());
    }


}
