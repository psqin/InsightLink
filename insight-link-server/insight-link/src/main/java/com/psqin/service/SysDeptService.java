package com.psqin.service;

import com.psqin.domain.entity.SysDept;
import com.psqin.result.PageResult;

import java.util.List;

public interface SysDeptService {

    List<SysDept> listCollegesByUniversityId(Long universityId);

    List<SysDept> listMajorsByCollegeId(Long collegeId);

    List<SysDept> listClassesByMajorId(Long majorId);

    void save(SysDept sysDept);

    void update(SysDept sysDept);

    void deleteById(Long id);

    PageResult pageQuery(Long universityId, Integer deptType, Long parentId, String name, Integer page, Integer pageSize);
}

