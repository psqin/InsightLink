package com.psqin.service;

import com.psqin.domain.entity.Universities;
import com.psqin.result.PageResult;

import java.util.List;

public interface UniversityService {

    /**
     * 模糊查询学校
     * @param name
     * @return
     */
    List<Universities> query(String name);

    /**
     * 根据id获取学校信息
     * @param id
     * @return
     */
    Universities getById(long id);

    void save(Universities universities);

    void update(Universities universities);

    void deleteById(Long id);

    PageResult pageQuery(String name, String code, Integer page, Integer pageSize);
}
